from __future__ import absolute_import
from typing import Optional, Tuple, Mapping, Any, Text

from django.utils.translation import ugettext as _
from django.conf import settings
from django.template.defaultfilters import slugify
from django.core.files import File
from django.http import HttpRequest
from jinja2 import Markup as mark_safe
import unicodedata

from zerver.lib.avatar_hash import user_avatar_hash
from zerver.lib.request import JsonableError
from zerver.lib.str_utils import force_text, force_str, NonBinaryStr

import boto3
import botocore
from mimetypes import guess_type, guess_extension

from zerver.lib.str_utils import force_bytes, force_str
from zerver.models import get_user_profile_by_email, get_user_profile_by_id
from zerver.models import Attachment
from zerver.models import Realm, UserProfile, Message

from six.moves import urllib
import base64
import os
import re
from PIL import Image, ImageOps
from six import binary_type
import io
import random
import logging

DEFAULT_AVATAR_SIZE = 100
MEDIUM_AVATAR_SIZE = 500

# Performance Note:
#
# For writing files to S3, the file could either be stored in RAM
# (if it is less than 2.5MiB or so) or an actual temporary file on disk.
#
# Because we set FILE_UPLOAD_MAX_MEMORY_SIZE to 0, only the latter case
# should occur in practice.
#
# This is great, because passing the pseudofile object that Django gives
# you to boto would be a pain.

# To come up with a s3 key we randomly generate a "directory". The
# "file name" is the original filename provided by the user run
# through a sanitization function.

attachment_url_re = re.compile(u'[/\-]user[\-_]uploads[/\.-].*?(?=[ )]|\Z)')

def attachment_url_to_path_id(attachment_url):
    # type: (Text) -> Text
    path_id_raw = re.sub(u'[/\-]user[\-_]uploads[/\.-]', u'', attachment_url)
    # Remove any extra '.' after file extension. These are probably added by the user
    return re.sub(u'[.]+$', u'', path_id_raw, re.M)

def sanitize_name(raw_value):
    # type: (NonBinaryStr) -> Text
    """
    Sanitizes a value to be safe to store in a Linux filesystem, in
    S3, and in a URL.  So unicode is allowed, but not special
    characters other than ".", "-", and "_".

    This implementation is based on django.utils.text.slugify; it is
    modified by:
    * hardcoding allow_unicode=True.
    * adding '.' and '_' to the list of allowed characters.
    * preserving the case of the value.
    """
    value = force_text(raw_value)
    value = unicodedata.normalize('NFKC', value)
    value = re.sub('[^\w\s._-]', '', value, flags=re.U).strip()
    return mark_safe(re.sub('[-\s]+', '-', value, flags=re.U))

def random_name(bytes=60):
    # type: (int) -> Text
    return base64.urlsafe_b64encode(os.urandom(bytes)).decode('utf-8')

class BadImageError(JsonableError):
    pass

def resize_avatar(image_data, size=DEFAULT_AVATAR_SIZE):
    # type: (binary_type, int) -> binary_type
    try:
        im = Image.open(io.BytesIO(image_data))
        im = ImageOps.fit(im, (size, size), Image.ANTIALIAS)
    except IOError:
        raise BadImageError("Could not decode avatar image; did you upload an image file?")
    out = io.BytesIO()
    im.save(out, format='png')
    return out.getvalue()

### Common

class ZulipUploadBackend(object):
    def upload_message_image(self, uploaded_file_name, content_type, file_data, user_profile, target_realm=None):
        # type: (Text, Optional[Text], binary_type, UserProfile, Optional[Realm]) -> Text
        raise NotImplementedError()

    def upload_avatar_image(self, user_file, user_profile, email):
        # type: (File, UserProfile, Text) -> None
        raise NotImplementedError()

    def delete_message_image(self, path_id):
        # type: (Text) -> bool
        raise NotImplementedError()

    def get_avatar_url(self, hash_key, medium=False):
        # type: (Text, bool) -> Text
        raise NotImplementedError()

    def ensure_medium_avatar_image(self, email):
        # type: (Text) -> None
        raise NotImplementedError()

### S3

def upload_image_to_s3(
        bucket_name,
        file_name,
        content_type,
        user_profile,
        contents):
    # type: (NonBinaryStr, Text, Optional[Text], UserProfile, binary_type) -> None
    client = boto3.client('s3',
                          aws_access_key_id=settings.S3_KEY,
                          aws_secret_access_key=settings.S3_SECRET_KEY)

    client.put_object(Body=contents, Bucket=force_str(bucket_name), Key=force_str(file_name),
                      Metadata={'user_profile_id': str(user_profile.id), 'realm_id': str(user_profile.realm_id)},
                      ContentType=force_str(content_type))

def get_file_info(request, user_file):
    # type: (HttpRequest, File) -> Tuple[Text, Optional[Text]]

    uploaded_file_name = user_file.name
    assert isinstance(uploaded_file_name, str)

    content_type = request.GET.get('mimetype')
    if content_type is None:
        guessed_type = guess_type(uploaded_file_name)[0]
        if guessed_type is not None:
            content_type = force_text(guessed_type)
    else:
        uploaded_file_name = uploaded_file_name + guess_extension(content_type)

    uploaded_file_name = urllib.parse.unquote(uploaded_file_name)
    return uploaded_file_name, content_type

def get_signed_upload_url(path):
    # type: (Text) -> Text
    client = boto3.client('s3',
                          aws_access_key_id=settings.S3_KEY,
                          aws_secret_access_key=settings.S3_SECRET_KEY)
    return force_text(client.generate_presigned_url('get_object',
                      Params = {'Bucket': settings.S3_AUTH_UPLOADS_BUCKET, 'Key': force_str(path)}, ExpiresIn=15))

def get_realm_for_filename(path):
    # type: (Text) -> Optional[int]
    session = boto3.Session(aws_access_key_id=settings.S3_KEY,
                            aws_secret_access_key=settings.S3_SECRET_KEY)
    s3 = session.resource('s3')
    # check the key exists or not
    try:
        s3.Object(settings.S3_AUTH_UPLOADS_BUCKET, path).load()
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            exists = False
        else:
            raise e
    else:
        exists = True
    if exists is False:
        return None
    obj = s3.Object(settings.S3_AUTH_UPLOADS_BUCKET, path)
    return get_user_profile_by_id(obj.metadata["user_profile_id"]).realm_id

class S3UploadBackend(ZulipUploadBackend):
    def upload_message_image(self, uploaded_file_name, content_type, file_data, user_profile, target_realm=None):
        # type: (Text, Optional[Text], binary_type, UserProfile, Optional[Realm]) -> Text
        bucket_name = settings.S3_AUTH_UPLOADS_BUCKET
        if target_realm is None:
            target_realm = user_profile.realm
        s3_file_name = "/".join([
            str(target_realm.id),
            random_name(18),
            sanitize_name(uploaded_file_name)
        ])
        url = "/user_uploads/%s" % (s3_file_name,)

        upload_image_to_s3(
            bucket_name,
            s3_file_name,
            content_type,
            user_profile,
            file_data
        )

        create_attachment(uploaded_file_name, s3_file_name, user_profile)
        return url

    def delete_message_image(self, path_id):
        # type: (Text) -> bool
        session = boto3.Session(aws_access_key_id=settings.S3_KEY,
                                aws_secret_access_key=settings.S3_SECRET_KEY)
        s3 = session.resource('s3')
        try:
            s3.Object(settings.S3_AUTH_UPLOADS_BUCKET, path_id).load()
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "404":
                exists = False
            else:
                raise e
        else:
            exists = True

        if exists:
            bucket = s3.Bucket(settings.S3_AUTH_UPLOADS_BUCKET)
            bucket.delete_objects(Delete={'Objects': [{'Key': path_id}]})
            return True

        file_name = path_id.split("/")[-1]
        logging.warning("%s does not exist. Its entry in the database will be removed." % (file_name,))
        return False

    def upload_avatar_image(self, user_file, user_profile, email):
        # type: (File, UserProfile, Text) -> None
        content_type = guess_type(user_file.name)[0]
        bucket_name = settings.S3_AVATAR_BUCKET
        s3_file_name = user_avatar_hash(email)

        image_data = user_file.read()
        upload_image_to_s3(
            bucket_name,
            s3_file_name + ".original",
            content_type,
            user_profile,
            image_data,
        )

        # custom 500px wide version
        resized_medium = resize_avatar(image_data, MEDIUM_AVATAR_SIZE)
        upload_image_to_s3(
            bucket_name,
            s3_file_name + "-medium.png",
            "image/png",
            user_profile,
            resized_medium
        )

        resized_data = resize_avatar(image_data)
        upload_image_to_s3(
            bucket_name,
            s3_file_name,
            'image/png',
            user_profile,
            resized_data,
        )
        # See avatar_url in avatar.py for URL.  (That code also handles the case
        # that users use gravatar.)

    def get_avatar_url(self, hash_key, medium=False):
        # type: (Text, bool) -> Text
        bucket = settings.S3_AVATAR_BUCKET
        medium_suffix = "-medium" if medium else ""
        # ?x=x allows templates to append additional parameters with &s
        return u"https://%s.s3.amazonaws.com/%s%s?x=x" % (bucket, medium_suffix, hash_key)

    def ensure_medium_avatar_image(self, email):
        # type: (Text) -> None
        user_profile = get_user_profile_by_email(email)
        email_hash = user_avatar_hash(email)
        s3_file_name = email_hash

        bucket_name = settings.S3_AVATAR_BUCKET

        client = boto3.client('s3',
                              aws_access_key_id=settings.S3_KEY,
                              aws_secret_access_key=settings.S3_SECRET_KEY)
        obj = client.get_object(Bucket=force_str(bucket_name), Key=email_hash)

        image_data = obj['Body'].read()

        resized_medium = resize_avatar(image_data, MEDIUM_AVATAR_SIZE)
        upload_image_to_s3(
            bucket_name,
            s3_file_name + "-medium.png",
            "image/png",
            user_profile,
            resized_medium
        )

### Local

def mkdirs(path):
    # type: (Text) -> None
    dirname = os.path.dirname(path)
    if not os.path.isdir(dirname):
        os.makedirs(dirname)

def write_local_file(type, path, file_data):
    # type: (Text, Text, binary_type) -> None
    file_path = os.path.join(settings.LOCAL_UPLOADS_DIR, type, path)
    mkdirs(file_path)
    with open(file_path, 'wb') as f:
        f.write(file_data)

def get_local_file_path(path_id):
    # type: (Text) -> Optional[Text]
    local_path = os.path.join(settings.LOCAL_UPLOADS_DIR, 'files', path_id)
    if os.path.isfile(local_path):
        return local_path
    else:
        return None

class LocalUploadBackend(ZulipUploadBackend):
    def upload_message_image(self, uploaded_file_name, content_type, file_data, user_profile, target_realm=None):
        # type: (Text, Optional[Text], binary_type, UserProfile, Optional[Realm]) -> Text
        # Split into 256 subdirectories to prevent directories from getting too big
        path = "/".join([
            str(user_profile.realm_id),
            format(random.randint(0, 255), 'x'),
            random_name(18),
            sanitize_name(uploaded_file_name)
        ])

        write_local_file('files', path, file_data)
        create_attachment(uploaded_file_name, path, user_profile)
        return '/user_uploads/' + path

    def delete_message_image(self, path_id):
        # type: (Text) -> bool
        file_path = os.path.join(settings.LOCAL_UPLOADS_DIR, 'files', path_id)
        if os.path.isfile(file_path):
            # This removes the file but the empty folders still remain.
            os.remove(file_path)
            return True

        file_name = path_id.split("/")[-1]
        logging.warning("%s does not exist. Its entry in the database will be removed." % (file_name,))
        return False

    def upload_avatar_image(self, user_file, user_profile, email):
        # type: (File, UserProfile, Text) -> None
        email_hash = user_avatar_hash(email)

        image_data = user_file.read()
        write_local_file('avatars', email_hash+'.original', image_data)

        resized_data = resize_avatar(image_data)
        write_local_file('avatars', email_hash+'.png', resized_data)

        resized_medium = resize_avatar(image_data, MEDIUM_AVATAR_SIZE)
        write_local_file('avatars', email_hash+'-medium.png', resized_medium)

    def get_avatar_url(self, hash_key, medium=False):
        # type: (Text, bool) -> Text
        # ?x=x allows templates to append additional parameters with &s
        medium_suffix = "-medium" if medium else ""
        return u"/user_avatars/%s%s.png?x=x" % (hash_key, medium_suffix)

    def ensure_medium_avatar_image(self, email):
        # type: (Text) -> None
        email_hash = user_avatar_hash(email)

        output_path = os.path.join(settings.LOCAL_UPLOADS_DIR, "avatars", email_hash + "-medium.png")
        if os.path.isfile(output_path):
            return

        image_path = os.path.join(settings.LOCAL_UPLOADS_DIR, "avatars", email_hash + ".original")
        image_data = open(image_path, "rb").read()
        resized_medium = resize_avatar(image_data, MEDIUM_AVATAR_SIZE)
        write_local_file('avatars', email_hash + '-medium.png', resized_medium)

# Common and wrappers
if settings.LOCAL_UPLOADS_DIR is not None:
    upload_backend = LocalUploadBackend() # type: ZulipUploadBackend
else:
    upload_backend = S3UploadBackend()

def delete_message_image(path_id):
    # type: (Text) -> bool
    return upload_backend.delete_message_image(path_id)

def upload_avatar_image(user_file, user_profile, email):
    # type: (File, UserProfile, Text) -> None
    upload_backend.upload_avatar_image(user_file, user_profile, email)

def upload_message_image(uploaded_file_name, content_type, file_data, user_profile, target_realm=None):
    # type: (Text, Optional[Text], binary_type, UserProfile, Optional[Realm]) -> Text
    return upload_backend.upload_message_image(uploaded_file_name, content_type, file_data,
                                               user_profile, target_realm=target_realm)

def claim_attachment(user_profile, path_id, message, is_message_realm_public):
    # type: (UserProfile, Text, Message, bool) -> bool
    try:
        attachment = Attachment.objects.get(path_id=path_id)
        attachment.messages.add(message)
        # Only the owner of the file has the right to elevate the permissions of a file.
        # This makes sure that a private file is not accidently made public by another user
        # by sending a message to a public stream that refers the private file.
        if attachment.owner == user_profile:
            attachment.is_realm_public = attachment.is_realm_public or is_message_realm_public
        attachment.save()
        return True
    except Attachment.DoesNotExist:
        raise JsonableError(_("The upload was not successful. Please reupload the file again in a new message."))
    return False

def create_attachment(file_name, path_id, user_profile):
    # type: (Text, Text, UserProfile) -> bool
    Attachment.objects.create(file_name=file_name, path_id=path_id, owner=user_profile, realm=user_profile.realm)
    return True

def upload_message_image_from_request(request, user_file, user_profile):
    # type: (HttpRequest, File, UserProfile) -> Text
    uploaded_file_name, content_type = get_file_info(request, user_file)
    return upload_message_image(uploaded_file_name, content_type, user_file.read(), user_profile)
