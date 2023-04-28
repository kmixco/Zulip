import $ from "jquery";

import * as channel from "./channel";
import * as compose from "./compose";
import * as compose_actions from "./compose_actions";
import * as compose_fade from "./compose_fade";
import * as compose_ui from "./compose_ui";
import * as narrow from "./narrow";
import * as overlays from "./overlays";
import * as people from "./people";
import * as popover_menus from "./popover_menus";

// This is only updated when user opens the scheduled messages overlay.
export let scheduled_messages_data = [];

export function override_scheduled_messages_data(data) {
    scheduled_messages_data = data;
}

export function edit_scheduled_message(scheduled_msg_id) {
    const scheduled_msg = scheduled_messages_data.find(
        (msg) => msg.message_id === scheduled_msg_id,
    );

    let compose_args;

    if (scheduled_msg.type === "stream") {
        compose_args = {
            type: "stream",
            stream: scheduled_msg.stream_name,
            topic: scheduled_msg.topic,
            content: scheduled_msg.content,
        };
    } else {
        const recipient_emails = [];
        if (scheduled_msg.to) {
            for (const recipient_id of scheduled_msg.to) {
                recipient_emails.push(people.get_by_user_id(recipient_id).email);
            }
        }
        compose_args = {
            type: scheduled_msg.type,
            private_message_recipient: recipient_emails.join(","),
            content: scheduled_msg.content,
        };
    }

    if (compose_args.type === "stream") {
        narrow.activate(
            [
                {operator: "stream", operand: compose_args.stream},
                {operator: "topic", operand: compose_args.topic},
            ],
            {trigger: "edit scheduled message"},
        );
    } else {
        narrow.activate([{operator: "dm", operand: compose_args.private_message_recipient}], {
            trigger: "edit scheduled message",
        });
    }

    overlays.close_overlay("scheduled");
    compose_fade.clear_compose();
    compose.clear_preview_area();
    compose_actions.start(compose_args.type, compose_args);
    compose_ui.autosize_textarea($("#compose-textarea"));
    $("#compose-textarea").attr("data-scheduled-message-id", scheduled_msg_id);
    popover_menus.show_schedule_confirm_button(scheduled_msg.formatted_send_at_time, true);
}

export function delete_scheduled_message(scheduled_msg_id) {
    channel.del({
        url: "/json/scheduled_messages/" + scheduled_msg_id,
        success() {
            // TODO: Do this via events received from the server in server_events_dispatch.
            if (overlays.scheduled_messages_open()) {
                $(
                    `#scheduled_messages_overlay .scheduled-message-row[data-message-id=${scheduled_msg_id}]`,
                ).remove();
            }
            if ($("#compose-textarea").attr("data-scheduled-message-id")) {
                const compose_scheduled_msg_id = $("#compose-textarea").attr(
                    "data-scheduled-message-id",
                );
                // If user deleted the scheduled message which is being edited in compose, we clear
                // the scheduled message id from there which converts this editing state into a normal
                // schedule message state. So, clicking "Schedule" will now create a new scheduled message.
                if (compose_scheduled_msg_id === scheduled_msg_id) {
                    $("#compose-textarea").removeAttr("data-scheduled-message-id");
                }
            }
        },
    });
}

export function delete_scheduled_message_if_sent_directly() {
    // Delete old scheduled message if it was sent.
    if ($("#compose-textarea").attr("data-scheduled-message-id")) {
        delete_scheduled_message($("#compose-textarea").attr("data-scheduled-message-id"));
        $("#compose-textarea").removeAttr("data-scheduled-message-id");
    }
}
