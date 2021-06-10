from typing import Any, Dict, Optional

from django.utils.translation import gettext as _

from zerver.lib.actions import do_set_user_display_setting, send_message_moved_breadcrumbs
from zerver.lib.exceptions import JsonableError
from zerver.lib.message import truncate_topic
from zerver.lib.streams import (
    access_stream_by_name,
    access_stream_for_send_message,
    subscribed_to_stream,
)
from zerver.lib.topic import messages_for_topic, user_message_exists_for_topic
from zerver.models import UserProfile


def process_zcommands(
    content: str, data: Optional[Dict[str, Any]], user_profile: UserProfile
) -> Dict[str, Any]:
    def change_mode_setting(
        command: str, switch_command: str, setting: str, setting_value: int
    ) -> str:
        msg = (
            "Changed to {command} mode! To revert "
            "{command} mode, type `/{switch_command}`.".format(
                command=command,
                switch_command=switch_command,
            )
        )
        do_set_user_display_setting(
            user_profile=user_profile, setting_name=setting, setting_value=setting_value
        )
        return msg

    if not content.startswith("/"):
        raise JsonableError(_("There should be a leading slash in the zcommand."))
    command = content[1:]

    if command == "ping":
        return {}
    elif command == "night":
        if user_profile.color_scheme == UserProfile.COLOR_SCHEME_NIGHT:
            return dict(msg="You are still in night mode.")
        return dict(
            msg=change_mode_setting(
                command=command,
                switch_command="day",
                setting="color_scheme",
                setting_value=UserProfile.COLOR_SCHEME_NIGHT,
            )
        )
    elif command == "day":
        if user_profile.color_scheme == UserProfile.COLOR_SCHEME_LIGHT:
            return dict(msg="You are still in day mode.")
        return dict(
            msg=change_mode_setting(
                command=command,
                switch_command="night",
                setting="color_scheme",
                setting_value=UserProfile.COLOR_SCHEME_LIGHT,
            )
        )
    elif command == "fluid-width":
        if user_profile.fluid_layout_width:
            return dict(msg="You are still in fluid width mode.")
        return dict(
            msg=change_mode_setting(
                command=command,
                switch_command="fixed-width",
                setting="fluid_layout_width",
                setting_value=True,
            )
        )
    elif command == "fixed-width":
        if not user_profile.fluid_layout_width:
            return dict(msg="You are still in fixed width mode.")
        return dict(
            msg=change_mode_setting(
                command=command,
                switch_command="fluid-width",
                setting="fluid_layout_width",
                setting_value=False,
            )
        )
    elif command == "digress":
        data_keys = [
            "old_stream",
            "old_topic",
            "new_stream",
            "new_topic",
        ]
        if not data or not all(key in data for key in data_keys):
            raise JsonableError(_("Invalid data."))

        if data["old_stream"] == data["new_stream"] and data["old_topic"] == data["new_topic"]:
            raise JsonableError(_("Cannot digress to the same topic."))

        (old_stream, ignored_old_stream_sub) = access_stream_by_name(
            user_profile, data["old_stream"]
        )

        (new_stream, ignored_new_stream_sub) = access_stream_by_name(
            user_profile, data["new_stream"]
        )

        # Because /digress is just a shortcut for manually sending messages,
        # we make sure that the user has permission to send messages to these
        # streams themselves.
        access_stream_for_send_message(user_profile, old_stream, None)
        access_stream_for_send_message(user_profile, new_stream, None)

        # Allow digressing from a topic only if it isn't empty for the user.
        error_message = _("Old topic #**{}>{}** does not exist.").format(
            data["old_stream"], data["old_topic"]
        )

        if old_stream.is_history_realm_public() or (
            subscribed_to_stream(user_profile, old_stream.id)
            and old_stream.is_history_public_to_subscribers()
        ):
            # Stream history is visible to the user. Allow digress if the topic
            # isn't empty (that is, at least one Message exists).
            messages = messages_for_topic(old_stream.recipient.id, data["old_topic"])
            if len(messages) < 1:
                raise JsonableError(error_message)

        if (not old_stream.is_public()) and (not old_stream.is_history_public_to_subscribers()):
            # Stream history isn't visible. Allow digress if there is at least
            # one UserMessage.
            if not user_message_exists_for_topic(
                user_profile=user_profile,
                recipient_id=old_stream.recipient_id,
                topic_name=data["old_topic"],
            ):
                raise JsonableError(error_message)

        data["new_topic"] = truncate_topic(data["new_topic"])
        old_thread_notification_string = _("{user} digressed to the new topic: {new_location}")
        new_thread_notification_string = _("{user} digressed this from old topic: {old_location}")
        send_message_moved_breadcrumbs(
            user_profile,
            old_stream,
            data["old_topic"],
            old_thread_notification_string,
            new_stream,
            data["new_topic"],
            new_thread_notification_string,
        )
        return {}
    raise JsonableError(_("No such command: {}").format(command))
