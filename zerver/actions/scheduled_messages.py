import datetime
from typing import List, Optional, Sequence, Tuple, Union

import orjson
from django.conf import settings
from django.db import transaction
from django.utils.timezone import now as timezone_now
from django.utils.translation import gettext as _

from zerver.actions.message_send import build_message_send_dict, check_message, do_send_messages
from zerver.actions.uploads import check_attachment_reference_change, do_claim_attachments
from zerver.lib.addressee import Addressee
from zerver.lib.exceptions import JsonableError
from zerver.lib.message import SendMessageRequest, render_markdown
from zerver.lib.scheduled_messages import access_scheduled_message
from zerver.models import (
    Client,
    Message,
    Realm,
    ScheduledMessage,
    UserProfile,
    get_user_by_delivery_email,
)
from zerver.tornado.django_api import send_event


def extract_stream_id(req_to: str) -> List[int]:
    # Recipient should only be a single stream ID.
    try:
        stream_id = int(req_to)
    except ValueError:
        raise JsonableError(_("Invalid data type for stream ID"))
    return [stream_id]


def extract_direct_message_recipient_ids(req_to: str) -> List[int]:
    try:
        user_ids = orjson.loads(req_to)
    except orjson.JSONDecodeError:
        user_ids = req_to

    if not isinstance(user_ids, list):
        raise JsonableError(_("Invalid data type for recipients"))

    for user_id in user_ids:
        if not isinstance(user_id, int):
            raise JsonableError(_("Recipient list may only contain user IDs"))

    return list(set(user_ids))


def check_schedule_message(
    sender: UserProfile,
    client: Client,
    recipient_type_name: str,
    message_to: Union[Sequence[str], Sequence[int]],
    topic_name: Optional[str],
    message_content: str,
    scheduled_message_id: Optional[int],
    deliver_at: datetime.datetime,
    realm: Optional[Realm] = None,
    forwarder_user_profile: Optional[UserProfile] = None,
) -> int:
    addressee = Addressee.legacy_build(sender, recipient_type_name, message_to, topic_name)
    send_request = check_message(
        sender,
        client,
        addressee,
        message_content,
        realm=realm,
        forwarder_user_profile=forwarder_user_profile,
    )
    send_request.deliver_at = deliver_at

    if scheduled_message_id is not None:
        return edit_scheduled_message(scheduled_message_id, send_request, sender)

    return do_schedule_messages([send_request], sender)[0]


def do_schedule_messages(
    send_message_requests: Sequence[SendMessageRequest], sender: UserProfile
) -> List[int]:
    scheduled_messages: List[Tuple[ScheduledMessage, SendMessageRequest]] = []

    for send_request in send_message_requests:
        scheduled_message = ScheduledMessage()
        scheduled_message.sender = send_request.message.sender
        scheduled_message.recipient = send_request.message.recipient
        topic_name = send_request.message.topic_name()
        scheduled_message.set_topic_name(topic_name=topic_name)
        rendering_result = render_markdown(
            send_request.message, send_request.message.content, send_request.realm
        )
        scheduled_message.content = send_request.message.content
        scheduled_message.rendered_content = rendering_result.rendered_content
        scheduled_message.sending_client = send_request.message.sending_client
        scheduled_message.stream = send_request.stream
        scheduled_message.realm = send_request.realm
        assert send_request.deliver_at is not None
        scheduled_message.scheduled_timestamp = send_request.deliver_at
        scheduled_message.delivery_type = ScheduledMessage.SEND_LATER

        scheduled_messages.append((scheduled_message, send_request))

    with transaction.atomic():
        ScheduledMessage.objects.bulk_create(
            [scheduled_message for scheduled_message, ignored in scheduled_messages]
        )
        for scheduled_message, send_request in scheduled_messages:
            if do_claim_attachments(
                scheduled_message, send_request.rendering_result.potential_attachment_path_ids
            ):
                scheduled_message.has_attachment = True
                scheduled_message.save(update_fields=["has_attachment"])

    event = {
        "type": "scheduled_messages",
        "op": "add",
        "scheduled_messages": [
            scheduled_message.to_dict() for scheduled_message, ignored in scheduled_messages
        ],
    }
    send_event(sender.realm, event, [sender.id])
    return [scheduled_message.id for scheduled_message, ignored in scheduled_messages]


def edit_scheduled_message(
    scheduled_message_id: int, send_request: SendMessageRequest, sender: UserProfile
) -> int:
    with transaction.atomic():
        scheduled_message_object = access_scheduled_message(sender, scheduled_message_id)

        # Handles the race between us initiating this transaction and user sending us the edit request.
        if scheduled_message_object.delivered is True:
            raise JsonableError(_("Scheduled message was already sent"))

        # Only override fields that user can change.
        scheduled_message_object.recipient = send_request.message.recipient
        topic_name = send_request.message.topic_name()
        scheduled_message_object.set_topic_name(topic_name=topic_name)
        rendering_result = render_markdown(
            send_request.message, send_request.message.content, send_request.realm
        )
        scheduled_message_object.content = send_request.message.content
        scheduled_message_object.rendered_content = rendering_result.rendered_content
        scheduled_message_object.sending_client = send_request.message.sending_client
        scheduled_message_object.stream = send_request.stream
        assert send_request.deliver_at is not None
        scheduled_message_object.scheduled_timestamp = send_request.deliver_at

        scheduled_message_object.has_attachment = check_attachment_reference_change(
            scheduled_message_object, rendering_result
        )

        scheduled_message_object.save()

    event = {
        "type": "scheduled_messages",
        "op": "update",
        "scheduled_message": scheduled_message_object.to_dict(),
    }
    send_event(sender.realm, event, [sender.id])
    return scheduled_message_id


def delete_scheduled_message(user_profile: UserProfile, scheduled_message_id: int) -> None:
    scheduled_message_object = access_scheduled_message(user_profile, scheduled_message_id)
    scheduled_message_id = scheduled_message_object.id
    scheduled_message_object.delete()

    event = {
        "type": "scheduled_messages",
        "op": "remove",
        "scheduled_message_id": scheduled_message_id,
    }
    send_event(user_profile.realm, event, [user_profile.id])


def construct_send_request(scheduled_message: ScheduledMessage) -> SendMessageRequest:
    message = Message()
    original_sender = scheduled_message.sender
    message.content = scheduled_message.content
    message.recipient = scheduled_message.recipient
    message.realm = scheduled_message.realm
    message.subject = scheduled_message.subject
    message.date_sent = timezone_now()
    message.sending_client = scheduled_message.sending_client

    delivery_type = scheduled_message.delivery_type
    if delivery_type == ScheduledMessage.SEND_LATER:
        message.sender = original_sender
    elif delivery_type == ScheduledMessage.REMIND:
        message.sender = get_user_by_delivery_email(
            settings.NOTIFICATION_BOT, original_sender.realm
        )

    return build_message_send_dict(
        message=message, stream=scheduled_message.stream, realm=scheduled_message.realm
    )


def send_scheduled_message(scheduled_message: ScheduledMessage) -> None:
    message_send_request = construct_send_request(scheduled_message)
    do_send_messages([message_send_request])
    scheduled_message.delivered = True
    scheduled_message.save(update_fields=["delivered"])
