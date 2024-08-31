import $ from "jquery";
import assert from "minimalistic-assert";
import type * as tippy from "tippy.js";

import render_add_saved_reply_modal from "../templates/add_saved_reply_modal.hbs";

import * as channel from "./channel";
import * as compose_ui from "./compose_ui";
import * as dialog_widget from "./dialog_widget";
import * as dropdown_widget from "./dropdown_widget";
import {$t_html} from "./i18n";
import * as saved_replies from "./saved_replies";
import type {StateData} from "./state_data";

let saved_reply_dropdown_widget: dropdown_widget.DropdownWidget;

function submit_create_saved_reply_form(): void {
    const title = $<HTMLInputElement>("#add-new-saved-reply-modal .title").val()?.trim();
    const content = $<HTMLInputElement>("#add-new-saved-reply-modal .content").val()?.trim();
    if (title && content) {
        dialog_widget.submit_api_request(channel.post, "/json/saved_replies", {title, content});
    }
}

function update_submit_button_state(): void {
    const title = $<HTMLInputElement>("#add-new-saved-reply-modal .title").val()?.trim();
    const content = $<HTMLInputElement>("#add-new-saved-reply-modal .content").val()?.trim();
    const $submit_button = $("#add-new-saved-reply-modal .dialog_submit_button");

    $submit_button.prop("disabled", true);
    if (title && content) {
        $submit_button.prop("disabled", false);
    }
}

function saved_reply_modal_post_render(): void {
    $("#add-new-saved-reply-modal").on("input", "input,textarea", update_submit_button_state);
}

export function rerender_dropdown_widget(): void {
    const options = saved_replies.get_options_for_dropdown_widget();
    saved_reply_dropdown_widget.list_widget?.replace_list_data(options);
}

function delete_saved_reply(saved_reply_id: string | undefined): void {
    assert(saved_reply_id !== undefined);
    void channel.del({
        url: "/json/saved_replies/" + saved_reply_id,
    });
}

function item_click_callback(
    event: JQuery.ClickEvent,
    dropdown: tippy.Instance,
    widget: dropdown_widget.DropdownWidget,
): void {
    event.preventDefault();
    event.stopPropagation();

    if (
        $(event.target).closest(".saved_replies-dropdown-list-container .dropdown-list-delete")
            .length
    ) {
        delete_saved_reply($(event.currentTarget).attr("data-unique-id"));
        return;
    }

    dropdown.hide();
    const current_value = widget.current_value;
    if (current_value === saved_replies.ADD_SAVED_REPLY_OPTION_ID) {
        dialog_widget.launch({
            html_heading: $t_html({defaultMessage: "Add a new saved reply"}),
            html_body: render_add_saved_reply_modal(),
            html_submit_button: $t_html({defaultMessage: "Save"}),
            id: "add-new-saved-reply-modal",
            form_id: "add-new-saved-reply-form",
            update_submit_disabled_state_on_change: true,
            on_click: submit_create_saved_reply_form,
            post_render: saved_reply_modal_post_render,
        });
    } else {
        const content = saved_replies
            .get_saved_replies()
            .find((saved_reply) => saved_reply.id === current_value)?.content;
        assert(content !== undefined);
        const $textarea = $<HTMLTextAreaElement>("textarea#compose-textarea");
        compose_ui.insert_syntax_and_focus(content, $textarea);
    }
}

export const initialize = (params: StateData["saved_replies"]): void => {
    saved_replies.set_saved_replies(params.saved_replies);

    saved_reply_dropdown_widget = new dropdown_widget.DropdownWidget({
        widget_name: "saved_replies",
        get_options: saved_replies.get_options_for_dropdown_widget,
        item_click_callback,
        $events_container: $("body"),
        unique_id_type: dropdown_widget.DataTypes.NUMBER,
        focus_target_on_hidden: false,
        prefer_top_start_placement: true,
        tippy_props: {
            // Using -100 as x offset makes saved reply icon be in the center
            // of the dropdown widget and 5 as y offset is what we use in compose
            // recipient dropdown widget.
            offset: [-100, 5],
        },
    });
    saved_reply_dropdown_widget.setup();
};
