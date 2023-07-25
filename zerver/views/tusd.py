import logging
import os
from typing import Any, Dict, Mapping

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.utils.translation import gettext as _

from zerver.decorator import internal_notify_view
from zerver.lib.exceptions import JsonableError
from zerver.lib.request import REQ, has_request_variables
from zerver.lib.response import json_success
from zerver.lib.upload import check_upload_within_quota, generate_message_upload_path, move_file
from zerver.lib.upload.base import create_attachment
from zerver.models import UserProfile


def handle_pre_create_hook(
    request: HttpRequest, user_profile: UserProfile, data: Dict[str, Any]
) -> HttpResponse:
    size_is_deferred = data["SizeIsDeferred"]
    if size_is_deferred:
        raise JsonableError(_("Deferred file size not allowed."))
    file_size = data["Size"]
    if file_size > settings.MAX_FILE_UPLOAD_SIZE * 1024 * 1024:
        raise JsonableError(
            _("Uploaded file is larger than the allowed limit of {max_file_size} MiB").format(
                max_file_size=settings.MAX_FILE_UPLOAD_SIZE
            )
        )
    check_upload_within_quota(user_profile.realm, file_size)
    return json_success(request)


def handle_pre_finish_hook(
    request: HttpRequest, user_profile: UserProfile, data: Dict[str, Any]
) -> HttpResponse:
    storage_type = data["Storage"]["Type"]
    if settings.LOCAL_UPLOADS_DIR is not None:
        computed_storage_type = "filestore"
    else:
        computed_storage_type = "s3store"
    assert storage_type == computed_storage_type

    upload_id = data["ID"]

    # Upload ID will be either UUID or UUID+s3_meta
    file_id = upload_id.split("+")[0]
    realm = user_profile.realm

    file_name = data["MetaData"]["filename"]
    file_size = data["Size"]
    path_id = generate_message_upload_path(str(realm.id), file_name)
    if storage_type == "filestore":
        old_path = data["Storage"]["Path"]
        assert settings.LOCAL_FILES_DIR is not None
        new_path = os.path.join(settings.LOCAL_FILES_DIR, path_id)
    elif storage_type == "s3store":
        old_path = data["Storage"]["Key"]
        new_path = path_id
    try:
        move_file(old_path, new_path)
    except Exception as e:
        logging.error("error moving tusd file %s: %s", old_path, e)
        raise JsonableError(_("Upload failed."))
    create_attachment(file_name, path_id, user_profile, realm, file_size, file_id)

    return json_success(request)


@internal_notify_view(is_tornado_view=False)
@has_request_variables
def handle_tusd_hook(
    request: HttpRequest,
    user_profile: UserProfile,
    payload: Mapping[str, Any] = REQ(argument_type="body"),
) -> HttpResponse:
    hook_name = request.META.get("HTTP_HOOK_NAME")
    body = payload["Upload"]

    if hook_name == "pre-create":
        return handle_pre_create_hook(request, user_profile, body)
    if hook_name == "pre-finish":
        return handle_pre_finish_hook(request, user_profile, body)
    raise JsonableError(_("Unexpected hook."))
