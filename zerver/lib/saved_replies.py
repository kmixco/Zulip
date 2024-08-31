from typing import Any

from django.utils.translation import gettext as _

from zerver.lib.exceptions import ResourceNotFoundError
from zerver.models import SavedReply, UserProfile
from zerver.tornado.django_api import send_event_on_commit


def do_create_saved_reply(
    title: str,
    content: str,
    user_profile: UserProfile,
) -> SavedReply:
    saved_reply = SavedReply.objects.create(
        realm=user_profile.realm,
        user_profile=user_profile,
        title=title,
        content=content,
    )

    event = {
        "type": "saved_replies",
        "op": "add",
        "saved_reply": saved_reply.to_api_dict(),
    }
    send_event_on_commit(user_profile.realm, event, [user_profile.id])

    return saved_reply


def do_get_saved_replies(user_profile: UserProfile) -> list[dict[str, Any]]:
    saved_replies = SavedReply.objects.filter(user_profile=user_profile)

    return [saved_reply.to_api_dict() for saved_reply in saved_replies]


def do_delete_saved_reply(
    saved_reply_id: int,
    user_profile: UserProfile,
) -> None:
    try:
        saved_reply = SavedReply.objects.get(id=saved_reply_id, user_profile=user_profile)
    except SavedReply.DoesNotExist:
        raise ResourceNotFoundError(_("Saved reply does not exist."))
    saved_reply.delete()

    event = {"type": "saved_replies", "op": "remove", "saved_reply_id": saved_reply_id}
    send_event_on_commit(user_profile.realm, event, [user_profile.id])
