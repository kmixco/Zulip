/* Compose box module responsible for the message's recipient */

import $ from "jquery";
import _ from "lodash";

// todo: fix circular import here
import * as compose_actions from "./compose_actions";
import * as compose_fade from "./compose_fade";
import * as compose_state from "./compose_state";
import * as compose_validate from "./compose_validate";
import {DropdownListWidget} from "./dropdown_list_widget";
import {$t} from "./i18n";
import * as narrow_state from "./narrow_state";
import {page_params} from "./page_params";
import * as settings_config from "./settings_config";
import * as stream_bar from "./stream_bar";
import * as stream_data from "./stream_data";
import * as util from "./util";

export let compose_recipient_widget;
const PRIVATE_MESSAGE = "Private Message";

function composing_to_current_topic_narrow() {
    return (
        util.lower_same(compose_state.stream_name(), narrow_state.stream() || "") &&
        util.lower_same(compose_state.topic(), narrow_state.topic() || "")
    );
}

function composing_to_current_private_message_narrow() {
    const compose_state_recipient = compose_state.private_message_recipient();
    const narrow_state_recipient = narrow_state.pm_emails_string();
    return (
        compose_state_recipient &&
        narrow_state_recipient &&
        _.isEqual(
            compose_state_recipient
                .split(",")
                .map((s) => s.trim())
                .sort(),
            narrow_state_recipient
                .split(",")
                .map((s) => s.trim())
                .sort(),
        )
    );
}

export function update_narrow_to_recipient_visibility() {
    const message_type = compose_state.get_message_type();
    if (message_type === "stream") {
        const stream_name = compose_state.stream_name();
        const stream_exists = Boolean(stream_data.get_stream_id(stream_name));

        if (
            stream_exists &&
            !composing_to_current_topic_narrow() &&
            compose_state.has_full_recipient()
        ) {
            $(".narrow_to_compose_recipients").toggleClass("invisible", false);
            return;
        }
    } else if (message_type === "private") {
        const recipients = compose_state.private_message_recipient();
        if (
            recipients &&
            !composing_to_current_private_message_narrow() &&
            compose_state.has_full_recipient()
        ) {
            $(".narrow_to_compose_recipients").toggleClass("invisible", false);
            return;
        }
    }
    $(".narrow_to_compose_recipients").toggleClass("invisible", true);
}

function update_fade() {
    if (!compose_state.composing()) {
        return;
    }

    const msg_type = compose_state.get_message_type();

    // It's possible that the new topic is not a resolved topic
    // so we clear the older warning.
    compose_validate.clear_topic_resolved_warning();

    compose_validate.warn_if_topic_resolved();
    compose_fade.set_focused_recipient(msg_type);
    compose_fade.update_all();
}

export function update_on_recipient_change() {
    update_fade();
    update_narrow_to_recipient_visibility();
}

export function open_compose_stream_dropup() {
    if ($("#id_compose_select_recipient").hasClass("open")) {
        return;
    }
    $("#id_compose_select_recipient > .dropdown-toggle").dropdown("toggle");
}

function switch_message_type(message_type) {
    $("#compose-content .alert").hide();

    compose_state.set_message_type(message_type);

    const opts = {
        message_type,
        trigger: "toggle message",
        stream: compose_state.stream_name(),
        topic: compose_state.topic(),
        private_message_recipient: compose_state.private_message_recipient(),
    };
    compose_actions.show_compose_box(message_type, opts);
}

export function on_compose_select_recipient_update(new_value) {
    const message_type = compose_state.get_message_type();
    if (new_value === PRIVATE_MESSAGE) {
        // TODO: maybe make a way for the dropdown to have a different
        // string show on the button than in the list.
        $("#compose_select_recipient_name").text($t({defaultMessage: "PM"}));
        if (message_type !== "private") {
            switch_message_type("private");
        }
        if (compose_state.private_message_recipient().length === 0) {
            $("#private_message_recipient").trigger("focus").trigger("select");
        }
    } else {
        const $stream_header_colorblock = $("#compose_recipient_selection_dropdown").find(
            ".stream_header_colorblock",
        );
        stream_bar.decorate(new_value, $stream_header_colorblock);
        if (message_type === "private") {
            switch_message_type("stream");
        }
        // Always move focus to the topic input even if it's not empty,
        // since it's likely the user will want to update the topic
        // after updating the stream.
        $("#stream_message_recipient_topic").trigger("focus").trigger("select");
    }
    update_on_recipient_change();
}

export function update_stream_dropdown_options() {
    compose_recipient_widget.replace_data(get_options_for_recipient_widget());
}

export function possibly_update_dropdown_selection(old_stream_name, new_stream_name) {
    const selected_stream = compose_state.stream_name();
    if (selected_stream === old_stream_name) {
        compose_state.set_stream_name(new_stream_name);
    }
}

function get_options_for_recipient_widget() {
    const options = stream_data
        .subscribed_subs()
        .filter((stream) => stream_data.can_post_messages_in_stream(stream))
        .map((stream) => ({
            name: stream.name,
            value: stream.name,
            stream,
        }))
        .sort((a, b) => {
            if (a.name.toLowerCase() < b.name.toLowerCase()) {
                return -1;
            }
            if (a.name.toLowerCase() > b.name.toLowerCase()) {
                return 1;
            }
            return 0;
        });
    if (
        page_params.realm_private_message_policy !==
        settings_config.private_message_policy_values.disabled.code
    ) {
        options.unshift({name: PRIVATE_MESSAGE, value: PRIVATE_MESSAGE});
    }
    return options;
}

export function initialize() {
    const opts = {
        widget_name: "compose_select_recipient",
        data: get_options_for_recipient_widget(),
        default_text: $t({defaultMessage: "Select a stream"}),
        value: null,
        on_update: on_compose_select_recipient_update,
    };
    compose_recipient_widget = new DropdownListWidget(opts);
    compose_recipient_widget.setup();

    $("#compose_select_recipient_widget").on("select", (e) => {
        // We often focus on input fields to bring the user to fill it out.
        // In this situation, a focus on the dropdown div opens the dropdown
        // menu so that the user can select an option.
        open_compose_stream_dropup();
        e.stopPropagation();
    });

    // `keyup` isn't relevant for streams since it registers as a change only
    // when an item in the dropdown is selected.
    $("#stream_message_recipient_topic,#private_message_recipient").on(
        "keyup",
        update_on_recipient_change,
    );
    // changes for the stream dropdown are handled in on_compose_select_recipient_update
    $("#stream_message_recipient_topic,#private_message_recipient").on("change", () => {
        update_on_recipient_change();
        compose_state.set_recipient_edited_manually(true);
    });
}
