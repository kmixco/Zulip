from django.http import HttpRequest, HttpResponse
from django.utils.translation import gettext as _

from zerver.lib.exceptions import JsonableError
from zerver.lib.response import json_success
from zerver.lib.saved_replies import (
    do_create_saved_reply,
    do_delete_saved_reply,
    do_get_saved_replies,
)
from zerver.lib.typed_endpoint import typed_endpoint
from zerver.models import SavedReply, UserProfile


def get_saved_replies(
    request: HttpRequest,
    user_profile: UserProfile,
) -> HttpResponse:
    return json_success(request, data={"saved_replies": do_get_saved_replies(user_profile)})


@typed_endpoint
def create_saved_reply(
    request: HttpRequest,
    user_profile: UserProfile,
    *,
    title: str,
    content: str,
) -> HttpResponse:
    title = title.strip()[: SavedReply.MAX_TITLE_LENGTH]
    content = content.strip()
    if title == "":
        raise JsonableError(_("Title cannot be empty."))
    if content == "":
        raise JsonableError(_("Content cannot be empty."))
    saved_reply = do_create_saved_reply(title, content, user_profile)
    return json_success(request, data={"saved_reply_id": saved_reply.id})


def delete_saved_reply(
    request: HttpRequest,
    user_profile: UserProfile,
    *,
    saved_reply_id: int,
) -> HttpResponse:
    do_delete_saved_reply(saved_reply_id, user_profile)
    return json_success(request)
