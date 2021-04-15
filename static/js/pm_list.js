import $ from "jquery";

import * as buddy_data from "./buddy_data";
import * as hash_util from "./hash_util";
import * as narrow_state from "./narrow_state";
import * as people from "./people";
import * as pm_conversations from "./pm_conversations";
import * as pm_list_dom from "./pm_list_dom";
import * as resize from "./resize";
import * as stream_popover from "./stream_popover";
import * as ui from "./ui";
import * as ui_util from "./ui_util";
import * as unread from "./unread";
import * as vdom from "./vdom";

let prior_dom;
let private_messages_open = false;

export function clear_for_testing() {
    prior_dom = undefined;
    private_messages_open = false;
}

// This module manages the "Private messages" section in the upper
// left corner of the app.  This was split out from stream_list.js.

function get_filter_li() {
    return $(".top_left_private_messages");
}

function set_count(count) {
    ui_util.update_unread_count_in_dom(get_filter_li(), count);
}

function remove_expanded_private_messages() {
    stream_popover.hide_topic_popover();
    ui.get_content_element($("#private-container")).empty();
}

export function close() {
    private_messages_open = false;
    prior_dom = undefined;
    remove_expanded_private_messages();
}

export function get_active_user_ids_string() {
    const filter = narrow_state.filter();

    if (!filter) {
        return undefined;
    }

    const emails = filter.operands("pm-with")[0];

    if (!emails) {
        return undefined;
    }

    return people.emails_strings_to_user_ids_string(emails);
}

export function _get_convos() {
    const private_messages = pm_conversations.recent.get();
    const display_messages = [];
    const active_user_ids_string = get_active_user_ids_string();

    for (const private_message_obj of private_messages) {
        const user_ids_string = private_message_obj.user_ids_string;
        const reply_to = people.user_ids_string_to_emails_string(user_ids_string);
        const recipients_string = people.get_recipients(user_ids_string);

        const num_unread = unread.num_unread_for_person(user_ids_string);

        const is_group = user_ids_string.includes(",");

        const is_active = user_ids_string === active_user_ids_string;

        let user_circle_class;
        let fraction_present;

        if (is_group) {
            user_circle_class = "user_circle_fraction";
            fraction_present = buddy_data.huddle_fraction_present(user_ids_string);
        } else {
            const user_id = Number.parseInt(user_ids_string, 10);
            user_circle_class = buddy_data.get_user_circle_class(user_id);
            const recipient_user_obj = people.get_by_user_id(user_id);

            if (recipient_user_obj.is_bot) {
                user_circle_class = "user_circle_green";
            }
        }

        const display_message = {
            recipients: recipients_string,
            user_ids_string,
            unread: num_unread,
            is_zero: num_unread === 0,
            is_active,
            url: hash_util.pm_with_uri(reply_to),
            user_circle_class,
            fraction_present,
            is_group,
        };
        display_messages.push(display_message);
    }

    return display_messages;
}

export function _build_private_messages_list() {
    const convos = _get_convos();
    const dom_ast = pm_list_dom.pm_ul(convos);
    return dom_ast;
}

export function update_private_messages(skip_narrow_state_check) {
    // As all_messages and recent topics view have no narrow associated
    // with them so if Private messages is clicked on the left sidebar then
    // in order to expand the private message container we need to skip
    // narrow state check. This flag is added to, handle left-sidebars clicks
    // on Private messages without affecting other codebase that uses it.
    if (!skip_narrow_state_check && !narrow_state.active()) {
        return;
    }

    if (private_messages_open) {
        const container = ui.get_content_element($("#private-container"));
        const new_dom = _build_private_messages_list();

        function replace_content(html) {
            container.html(html);
        }

        function find() {
            return container.find("ul");
        }

        vdom.update(replace_content, find, new_dom, prior_dom);
        prior_dom = new_dom;
    }
}

export function is_all_privates() {
    const filter = narrow_state.filter();

    if (!filter) {
        return false;
    }

    return filter.operands("is").includes("private");
}

export function expand() {
    private_messages_open = true;
    stream_popover.hide_topic_popover();
    const skip_narrow_state_check = true;
    update_private_messages(skip_narrow_state_check);
    if (is_all_privates()) {
        $(".top_left_private_messages").addClass("active-filter");
    }
}

export function update_dom_with_unread_counts(counts) {
    update_private_messages();
    set_count(counts.private_message_count);
}

export function handle_private_message_sidebar_click() {
    if (!private_messages_open) {
        expand();
        resize.resize_stream_filters_container();
    }
}
