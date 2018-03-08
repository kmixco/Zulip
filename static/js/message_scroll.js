var message_scroll = (function () {

var exports = {};

var actively_scrolling = false;

var loading_more_messages_indicator_showing = false;
exports.show_loading_more_messages_indicator = function () {
    if (! loading_more_messages_indicator_showing) {
        loading.make_indicator($('#loading_more_messages_indicator'),
                                    {abs_positioned: true});
        loading_more_messages_indicator_showing = true;
        floating_recipient_bar.hide();
    }
};

exports.hide_loading_more_messages_indicator = function () {
    if (loading_more_messages_indicator_showing) {
        loading.destroy_indicator($("#loading_more_messages_indicator"));
        loading_more_messages_indicator_showing = false;
    }
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
        pointer.suppress_scroll_pointer_update = false;
    }

    floating_recipient_bar.update();

    if (message_viewport.scrollTop() === 0) {
        message_fetch.load_more_messages({
            msg_list: current_msg_list,
            show_loading: exports.show_loading_more_messages_indicator,
            hide_loading: exports.hide_loading_more_messages_indicator,
        });
    }

    // When the window scrolls, it may cause some messages to
    // enter the screen and become read.  Calling
    // unread_ops.process_visible will update necessary
    // data structures and DOM elements.
    setTimeout(unread_ops.process_visible, 0);
};

var scroll_timer;
function scroll_finish() {
    actively_scrolling = true;
    clearTimeout(scroll_timer);
    scroll_timer = setTimeout(exports.scroll_finished, 100);
}

exports.initialize = function () {
    message_viewport.message_pane.scroll($.throttle(50, function () {
        unread_ops.process_visible();
        scroll_finish();
    }));
};


return exports;

}());
if (typeof module !== 'undefined') {
    module.exports = message_scroll;
}
