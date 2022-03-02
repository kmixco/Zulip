import datetime
from typing import List, Optional, Union

import orjson
from django.contrib.auth.models import AnonymousUser
from django.db import IntegrityError, transaction
from django.http import HttpRequest, HttpResponse
from django.utils.timezone import now as timezone_now
from django.utils.translation import gettext as _

from zerver.context_processors import get_valid_realm_from_request
from zerver.lib.actions import check_update_message, do_delete_messages
from zerver.lib.exceptions import JsonableError
from zerver.lib.html_diff import highlight_html_differences
from zerver.lib.message import access_message, access_web_public_message
from zerver.lib.request import REQ, RequestNotes, has_request_variables
from zerver.lib.response import json_success
from zerver.lib.timestamp import datetime_to_timestamp
from zerver.lib.topic import LEGACY_PREV_TOPIC, REQ_topic
from zerver.lib.types import EditHistoryEvent, FormattedEditHistoryEvent
from zerver.lib.validator import check_bool, check_string_in, to_non_negative_int
from zerver.models import Message, UserProfile


def fill_edit_history_entries(
    raw_edit_history: List[EditHistoryEvent], message: Message
) -> List[FormattedEditHistoryEvent]:
    """This fills out the message edit history entries from the database,
    which are designed to have the minimum data possible, to instead
    have the current topic + content as of that time, plus data on
    whatever changed.  This makes it much simpler to do future
    processing.

    Note that this mutates what is passed to it, which is sorta a bad pattern.
    """
    prev_content = message.content
    prev_rendered_content = message.rendered_content
    prev_topic = message.topic_name()

    # Make sure that the latest entry in the history corresponds to the
    # message's last edit time
    if len(raw_edit_history) > 0:
        assert message.last_edit_time is not None
        assert datetime_to_timestamp(message.last_edit_time) == raw_edit_history[0]["timestamp"]

    formatted_edit_history: List[FormattedEditHistoryEvent] = []
    for edit_history_event in raw_edit_history:
        formatted_entry: FormattedEditHistoryEvent = {
            "content": prev_content,
            "rendered_content": prev_rendered_content,
            "timestamp": edit_history_event["timestamp"],
            "topic": prev_topic,
            "user_id": edit_history_event["user_id"],
        }

        # Add current topic, map LEGACY_PREV_TOPIC => "prev_topic".
        if LEGACY_PREV_TOPIC in edit_history_event:
            prev_topic = edit_history_event["prev_subject"]
            formatted_entry["prev_topic"] = prev_topic

        # Fill current values for content/rendered_content.
        if "prev_content" in edit_history_event:
            formatted_entry["prev_content"] = edit_history_event["prev_content"]
            prev_content = formatted_entry["prev_content"]
            formatted_entry["prev_rendered_content"] = edit_history_event["prev_rendered_content"]
            prev_rendered_content = formatted_entry["prev_rendered_content"]
            assert prev_rendered_content is not None
            rendered_content = formatted_entry["rendered_content"]
            assert rendered_content is not None
            formatted_entry["content_html_diff"] = highlight_html_differences(
                prev_rendered_content, rendered_content, message.id
            )

        if "prev_stream" in edit_history_event:
            formatted_entry["prev_stream"] = edit_history_event["prev_stream"]
            # TODO: Include current stream here.

    formatted_edit_history.append(
        FormattedEditHistoryEvent(
            dict(
                topic=prev_topic,
                content=prev_content,
                rendered_content=prev_rendered_content,
                timestamp=datetime_to_timestamp(message.date_sent),
                user_id=message.sender_id,
            )
        )
    )
    return formatted_edit_history


@has_request_variables
def get_message_edit_history(
    request: HttpRequest,
    user_profile: UserProfile,
    message_id: int = REQ(converter=to_non_negative_int, path_only=True),
) -> HttpResponse:
    if not user_profile.realm.allow_edit_history:
        raise JsonableError(_("Message edit history is disabled in this organization"))
    message, ignored_user_message = access_message(user_profile, message_id)

    # Extract the message edit history from the message
    if message.edit_history is not None:
        raw_edit_history = orjson.loads(message.edit_history)
    else:
        raw_edit_history = []

    # Fill in all the extra data that will make it usable
    message_edit_history = fill_edit_history_entries(raw_edit_history, message)
    return json_success(request, data={"message_history": list(reversed(message_edit_history))})


PROPAGATE_MODE_VALUES = ["change_later", "change_one", "change_all"]


@has_request_variables
def update_message_backend(
    request: HttpRequest,
    user_profile: UserProfile,
    message_id: int = REQ(converter=to_non_negative_int, path_only=True),
    stream_id: Optional[int] = REQ(converter=to_non_negative_int, default=None),
    topic_name: Optional[str] = REQ_topic(),
    propagate_mode: str = REQ(
        default="change_one", str_validator=check_string_in(PROPAGATE_MODE_VALUES)
    ),
    send_notification_to_old_thread: bool = REQ(default=True, json_validator=check_bool),
    send_notification_to_new_thread: bool = REQ(default=True, json_validator=check_bool),
    content: Optional[str] = REQ(default=None),
) -> HttpResponse:
    number_changed = check_update_message(
        user_profile,
        message_id,
        stream_id,
        topic_name,
        propagate_mode,
        send_notification_to_old_thread,
        send_notification_to_new_thread,
        content,
    )

    # Include the number of messages changed in the logs
    log_data = RequestNotes.get_notes(request).log_data
    assert log_data is not None
    log_data["extra"] = f"[{number_changed}]"

    return json_success(request)


def validate_can_delete_message(user_profile: UserProfile, message: Message) -> None:
    if user_profile.is_realm_admin:
        # Admin can delete any message, any time.
        return
    if message.sender != user_profile:
        # Users can only delete messages sent by them.
        raise JsonableError(_("You don't have permission to delete this message"))
    if not user_profile.can_delete_own_message():
        # Only user with roles as allowed by delete_own_message_policy can delete message.
        raise JsonableError(_("You don't have permission to delete this message"))

    deadline_seconds: Optional[int] = user_profile.realm.message_content_delete_limit_seconds
    if deadline_seconds is None:
        # None means no time limit to delete message
        return
    if (timezone_now() - message.date_sent) > datetime.timedelta(seconds=deadline_seconds):
        # User can not delete message after deadline time of realm
        raise JsonableError(_("The time limit for deleting this message has passed"))
    return


@transaction.atomic
@has_request_variables
def delete_message_backend(
    request: HttpRequest,
    user_profile: UserProfile,
    message_id: int = REQ(converter=to_non_negative_int, path_only=True),
) -> HttpResponse:
    # We lock the `Message` object to ensure that any transactions modifying the `Message` object
    # concurrently are serialized properly with deleting the message; this prevents a deadlock
    # that would otherwise happen because of the other transaction holding a lock on the `Message`
    # row.
    message, ignored_user_message = access_message(user_profile, message_id, lock_message=True)
    validate_can_delete_message(user_profile, message)
    try:
        do_delete_messages(user_profile.realm, [message])
    except (Message.DoesNotExist, IntegrityError):
        raise JsonableError(_("Message already deleted"))
    return json_success(request)


@has_request_variables
def json_fetch_raw_message(
    request: HttpRequest,
    maybe_user_profile: Union[UserProfile, AnonymousUser],
    message_id: int = REQ(converter=to_non_negative_int, path_only=True),
) -> HttpResponse:

    if not maybe_user_profile.is_authenticated:
        realm = get_valid_realm_from_request(request)
        message = access_web_public_message(realm, message_id)
    else:
        (message, user_message) = access_message(maybe_user_profile, message_id)

    return json_success(request, data={"raw_content": message.content})
