let actively_scrolling = false;

let loading_older_messages_indicator_showing = false;
let loading_newer_messages_indicator_showing = false;
exports.show_loading_older = function () {
    if (!loading_older_messages_indicator_showing) {
        loading.make_indicator($('#loading_older_messages_indicator'),
                               {abs_positioned: true});
        loading_older_messages_indicator_showing = true;
        floating_recipient_bar.hide();
    }
};

exports.hide_loading_older = function () {
    if (loading_older_messages_indicator_showing) {
        loading.destroy_indicator($("#loading_older_messages_indicator"));
        loading_older_messages_indicator_showing = false;
    }
};

exports.show_loading_newer = function () {
    if (!loading_newer_messages_indicator_showing) {
        $(".bottom-messages-logo").show();
        loading.make_indicator($('#loading_newer_messages_indicator'),
                               {abs_positioned: true});
        loading_newer_messages_indicator_showing = true;
        floating_recipient_bar.hide();
    }
};

exports.hide_loading_newer = function () {
    if (loading_newer_messages_indicator_showing) {
        $(".bottom-messages-logo").hide();
        loading.destroy_indicator($("#loading_newer_messages_indicator"));
        loading_newer_messages_indicator_showing = false;
    }
};

exports.hide_indicators = function () {
    exports.hide_loading_older();
    exports.hide_loading_newer();
};

exports.show_history_limit_notice = function () {
    $(".top-messages-logo").hide();
    $(".history-limited-box").show();
    exports.hide_empty_narrow_message();
};

exports.hide_history_limit_notice = function () {
    $(".top-messages-logo").show();
    $(".history-limited-box").hide();
};

exports.hide_end_of_results_notice = function () {
    $(".all-messages-search-caution").hide();
};

exports.show_end_of_results_notice = function () {
    $(".all-messages-search-caution").show();
    // Set the link to point to this search with streams:public added.
    // It's a bit hacky to use the href, but
    // !filter.includes_full_stream_history() implies streams:public
    // wasn't already present.
    $(".all-messages-search-caution a.search-shared-history").attr(
        "href", window.location.hash.replace("#narrow/", "#narrow/streams/public/")
    );
};

exports.update_top_of_narrow_notices = function (msg_list) {
    if (msg_list !== current_msg_list) {
        return;
    }

    if (msg_list.data.fetch_status.has_found_oldest() &&
        current_msg_list !== home_msg_list) {
        const filter = narrow_state.filter();
        // Potentially display the notice that lets users know
        // that not all messages were searched.  One could
        // imagine including `filter.is_search()` in these
        // conditions, but there's a very legitimate use case
        // for moderation of searching for all messages sent
        // by a potential spammer user.
        if (!filter.contains_only_private_messages() &&
            !filter.includes_full_stream_history() &&
            !filter.is_personal_filter()) {
            exports.show_end_of_results_notice();
        }
    }

    if (msg_list.data.fetch_status.history_limited()) {
        exports.show_history_limit_notice();
    }
};

exports.hide_top_of_narrow_notices = function () {
    exports.hide_end_of_results_notice();
    exports.hide_history_limit_notice();
};

exports.actively_scrolling = function () {
    return actively_scrolling;
};

exports.scroll_finished = function () {
    actively_scrolling = false;

    if (!$('#home').hasClass('active')) {
        return;
    }

    if (!pointer.suppress_scroll_pointer_update) {
        message_viewport.keep_pointer_in_view();
    } else {
        pointer.set_suppress_scroll_pointer_update(false);
    }

    floating_recipient_bar.update();

    if (message_viewport.at_top()) {
        message_fetch.maybe_load_older_messages({
            msg_list: current_msg_list,
        });
    }

    if (message_viewport.at_bottom()) {
        message_fetch.maybe_load_newer_messages({
            msg_list: current_msg_list,
        });
    }

    // When the window scrolls, it may cause some messages to
    // enter the screen and become read.  Calling
    // unread_ops.process_visible will update necessary
    // data structures and DOM elements.
    setTimeout(unread_ops.process_visible, 0);
};

let scroll_timer;
function scroll_finish() {
    actively_scrolling = true;
    clearTimeout(scroll_timer);
    scroll_timer = setTimeout(exports.scroll_finished, 100);
}

exports.initialize = function () {
    message_viewport.message_pane.scroll(_.throttle(function () {
        unread_ops.process_visible();
        scroll_finish();
    }, 50));
};


window.message_scroll = exports;
