import $ from "jquery";

import * as typing_status from "../shared/src/typing_status";

import * as blueslip from "./blueslip";
import * as channel from "./channel";
import * as compose_pm_pill from "./compose_pm_pill";
import * as compose_state from "./compose_state";
import {page_params} from "./page_params";
import * as people from "./people";
import * as rows from "./rows";
import {user_settings} from "./user_settings";

// This module handles the outbound side of typing indicators.
// We detect changes in the compose box and notify the server
// when we are typing.  For the inbound side see typing_events.js.
//
// See docs/subsystems/typing-indicators.md for details on typing indicators.

function send_typing_notification_ajax(user_ids_array, operation, message_id) {
    channel.post({
        url: "/json/typing",
        data: {
            to: JSON.stringify(user_ids_array),
            op: operation,
            message_id: JSON.stringify(message_id),
        },
        success() {},
        error(xhr) {
            blueslip.warn("Failed to send typing event: " + xhr.responseText);
        },
    });
}

function get_user_ids_array() {
    const user_ids_string = compose_pm_pill.get_user_ids_string();
    if (user_ids_string === "") {
        return null;
    }

    return people.user_ids_string_to_ids_array(user_ids_string);
}

function is_valid_conversation() {
    const compose_empty = !compose_state.has_message_content();
    if (compose_empty) {
        return false;
    }

    return true;
}

function get_current_time() {
    return Date.now();
}

function notify_server_start(user_ids_array, message_id) {
    if (user_settings.send_private_typing_notifications) {
        send_typing_notification_ajax(user_ids_array, "start", message_id);
    }
}

function notify_server_stop(user_ids_array, message_id) {
    if (user_settings.send_private_typing_notifications) {
        send_typing_notification_ajax(user_ids_array, "stop", message_id);
    }
}

export const get_recipient = get_user_ids_array;

export function initialize() {
    const worker = {
        get_current_time,
        notify_server_start,
        notify_server_stop,
    };

    $(document).on("input", "#compose-textarea", () => {
        // If our previous state was no typing notification, send a
        // start-typing notice immediately.
        const new_recipient = is_valid_conversation() ? get_recipient() : null;
        typing_status.update(worker, new_recipient);
    });

    // We send a stop-typing notification immediately when compose is
    // closed/cancelled
    $(document).on("compose_canceled.zulip compose_finished.zulip", () => {
        typing_status.update(worker, null);
    });

    let message_being_edited = null;

    $("body").on("input", ".message_edit_content", (e) => {
        // If our previous state was no typing notification, send a
        // start-typing notice immediately for editing messages.
        const message_id = rows.id($(e.currentTarget).closest(".message_row"));
        message_being_edited = message_id;
        const new_recipient = [page_params.user_id];
        typing_status.update(worker, new_recipient, message_id);
    });

    // We send a stop-typing notification immediately when the message
    // being edited is saved/cancelled
    $("body").on("click", ".message_edit_save, .message_edit_cancel", () => {
        // const message_id = rows.id($(e.currentTarget).closest(".message_row"));
        const message_id = message_being_edited;
        typing_status.update(worker, null, message_id);
        message_being_edited = null;
    });
}
