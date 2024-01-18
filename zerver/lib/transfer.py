import logging
import os
from mimetypes import guess_type

from django.conf import settings

from zerver.lib.avatar_hash import user_avatar_path
from zerver.lib.parallel import run_parallel
from zerver.lib.upload.s3 import S3UploadBackend, upload_image_to_s3
from zerver.models import Attachment, RealmEmoji, UserProfile

s3backend = S3UploadBackend()


def transfer_uploads_to_s3(processes: int) -> None:
    # TODO: Eventually, we'll want to add realm icon and logo
    transfer_avatars_to_s3(processes)
    transfer_message_files_to_s3(processes)
    transfer_emoji_to_s3(processes)


def _transfer_avatar_to_s3(user: UserProfile) -> None:
    avatar_path = user_avatar_path(user)
    assert settings.LOCAL_UPLOADS_DIR is not None
    assert settings.LOCAL_AVATARS_DIR is not None
    file_path = os.path.join(settings.LOCAL_AVATARS_DIR, avatar_path) + ".original"
    try:
        with open(file_path, "rb") as f:
            s3backend.upload_avatar_image(f, user, user)
            logging.info("Uploaded avatar for %s in realm %s", user.id, user.realm.name)
    except FileNotFoundError:
        pass


def transfer_avatars_to_s3(processes: int) -> None:
    run_parallel(_transfer_avatar_to_s3, UserProfile.objects.all(), processes)


def _transfer_message_files_to_s3(attachment: Attachment) -> None:
    assert settings.LOCAL_UPLOADS_DIR is not None
    assert settings.LOCAL_FILES_DIR is not None
    file_path = os.path.join(settings.LOCAL_FILES_DIR, attachment.path_id)
    try:
        with open(file_path, "rb") as f:
            guessed_type = guess_type(attachment.file_name)[0]
            upload_image_to_s3(
                s3backend.uploads_bucket,
                attachment.path_id,
                guessed_type,
                attachment.owner,
                f.read(),
                settings.S3_UPLOADS_STORAGE_CLASS,
            )
            logging.info("Uploaded message file in path %s", file_path)
    except FileNotFoundError:  # nocoverage
        pass


def transfer_message_files_to_s3(processes: int) -> None:
    run_parallel(_transfer_message_files_to_s3, Attachment.objects.all(), processes)


def _transfer_emoji_to_s3(realm_emoji: RealmEmoji) -> None:
    if not realm_emoji.file_name or not realm_emoji.author:
        return  # nocoverage
    emoji_path = RealmEmoji.PATH_ID_TEMPLATE.format(
        realm_id=realm_emoji.realm.id,
        emoji_file_name=realm_emoji.file_name,
    )
    assert settings.LOCAL_UPLOADS_DIR is not None
    assert settings.LOCAL_AVATARS_DIR is not None
    emoji_path = os.path.join(settings.LOCAL_AVATARS_DIR, emoji_path) + ".original"
    try:
        with open(emoji_path, "rb") as f:
            s3backend.upload_emoji_image(f, realm_emoji.file_name, realm_emoji.author)
            logging.info("Uploaded emoji file in path %s", emoji_path)
    except FileNotFoundError:  # nocoverage
        pass


def transfer_emoji_to_s3(processes: int) -> None:
    run_parallel(_transfer_emoji_to_s3, RealmEmoji.objects.filter(), processes)
