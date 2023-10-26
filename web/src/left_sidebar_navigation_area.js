import $ from "jquery";

import * as resize from "./resize";
import * as scheduled_messages from "./scheduled_messages";
import * as settings_config from "./settings_config";
import * as ui_util from "./ui_util";

let last_mention_count = 0;

export function update_starred_count(count) {
    const $starred_li = $(".top_left_starred_messages");
    ui_util.update_unread_count_in_dom($starred_li, count);
}

export function update_scheduled_messages_row() {
    const $scheduled_li = $(".top_left_scheduled_messages");
    const count = scheduled_messages.get_count();
    if (count > 0) {
        $scheduled_li.addClass("show-with-scheduled-messages");
    } else {
        $scheduled_li.removeClass("show-with-scheduled-messages");
    }
    ui_util.update_unread_count_in_dom($scheduled_li, count);
}

export function update_dom_with_unread_counts(counts, skip_animations) {
    // Note that direct message counts are handled in pm_list.js.

    // mentioned/inbox have simple integer counts
    const $mentioned_li = $(".top_left_mentions");
    const $inbox_li = $(".top_left_inbox");

    ui_util.update_unread_count_in_dom($mentioned_li, counts.mentioned_message_count);
    ui_util.update_unread_count_in_dom($inbox_li, counts.home_unread_messages);

    if (!skip_animations) {
        animate_mention_changes($mentioned_li, counts.mentioned_message_count);
    }
}

// TODO: Rewrite how we handle activation of narrows when doing the redesign.
// We don't want to adjust class for all the buttons when switching narrows.

function remove($elem) {
    $elem.removeClass("active-filter active-sub-filter");
}

export function deselect_top_left_corner_items() {
    remove($(".top_left_all_messages"));
    remove($(".top_left_starred_messages"));
    remove($(".top_left_mentions"));
    remove($(".top_left_recent_view"));
    remove($(".top_left_inbox"));
}

export function handle_narrow_activated(filter) {
    deselect_top_left_corner_items();

    let ops;
    let filter_name;
    let $filter_li;

    // TODO: handle confused filters like "in:all stream:foo"
    ops = filter.operands("in");
    if (ops.length >= 1) {
        filter_name = ops[0];
        if (filter_name === "home") {
            $filter_li = $(".top_left_all_messages");
            $filter_li.addClass("active-filter");
        }
    }
    ops = filter.operands("is");
    if (ops.length >= 1) {
        filter_name = ops[0];
        if (filter_name === "starred") {
            $filter_li = $(".top_left_starred_messages");
            $filter_li.addClass("active-filter");
        } else if (filter_name === "mentioned") {
            $filter_li = $(".top_left_mentions");
            $filter_li.addClass("active-filter");
        }
    }
}

function toggle_condensed_navigation_area() {
    const $views_label_container = $("#views-label-container");
    const $views_label_icon = $("#toggle-top-left-navigation-area-icon");
    if ($views_label_container.hasClass("showing-expanded-navigation")) {
        // Toggle into the condensed state
        $views_label_container.addClass("showing-condensed-navigation");
        $views_label_container.removeClass("showing-expanded-navigation");
        $views_label_icon.addClass("fa-caret-right");
        $views_label_icon.removeClass("fa-caret-down");
    } else {
        // Toggle into the expanded state
        $views_label_container.addClass("showing-expanded-navigation");
        $views_label_container.removeClass("showing-condensed-navigation");
        $views_label_icon.addClass("fa-caret-down");
        $views_label_icon.removeClass("fa-caret-right");
    }
}

export function highlight_recent_view() {
    remove($(".top_left_all_messages"));
    remove($(".top_left_starred_messages"));
    remove($(".top_left_mentions"));
    remove($(".top_left_inbox"));
    $(".top_left_recent_view").addClass("active-filter");
    setTimeout(() => {
        resize.resize_stream_filters_container();
    }, 0);
}

export function animate_mention_changes($li, new_mention_count) {
    if (new_mention_count > last_mention_count) {
        do_new_messages_animation($li);
    }
    last_mention_count = new_mention_count;
}

function do_new_messages_animation($li) {
    $li.addClass("new_messages");
    function mid_animation() {
        $li.removeClass("new_messages");
        $li.addClass("new_messages_fadeout");
    }
    function end_animation() {
        $li.removeClass("new_messages_fadeout");
    }
    setTimeout(mid_animation, 3000);
    setTimeout(end_animation, 6000);
}

export function highlight_inbox_view() {
    remove($(".top_left_all_messages"));
    remove($(".top_left_starred_messages"));
    remove($(".top_left_recent_view"));
    remove($(".top_left_mentions"));
    $(".top_left_inbox").addClass("active-filter");
    setTimeout(() => {
        resize.resize_stream_filters_container();
    }, 0);
}

export function handle_home_view_changed(new_home_view) {
    const $recent_view_sidebar_menu_icon = $(".recent-view-sidebar-menu-icon");
    const $all_messages_sidebar_menu_icon = $(".all-messages-sidebar-menu-icon");
    if (new_home_view === settings_config.web_home_view_values.all_messages.code) {
        $recent_view_sidebar_menu_icon.removeClass("hide");
        $all_messages_sidebar_menu_icon.addClass("hide");
    } else if (new_home_view === settings_config.web_home_view_values.recent_topics.code) {
        $recent_view_sidebar_menu_icon.addClass("hide");
        $all_messages_sidebar_menu_icon.removeClass("hide");
    } else {
        // Inbox is home view.
        $recent_view_sidebar_menu_icon.removeClass("hide");
        $all_messages_sidebar_menu_icon.removeClass("hide");
    }
}

export function initialize() {
    update_scheduled_messages_row();

    $("body").on("click", "#views-label-container", (e) => {
        if (
            $(e.currentTarget).hasClass("showing-condensed-navigation") &&
            !($(e.target).hasClass("sidebar-title") || $(e.target).hasClass("fa-caret-right"))
        ) {
            // Ignore clicks on condensed nav items
            return;
        }
        e.stopPropagation();
        toggle_condensed_navigation_area();
    });
}
