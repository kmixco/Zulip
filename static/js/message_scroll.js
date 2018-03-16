var message_scroll = (function () {

var exports = {};

var actively_scrolling = false;

var loading_more_messages_indicator_showing = false;
exports.show_loading_older = function () {
    if (! loading_more_messages_indicator_showing) {
        loading.make_indicator($('#loading_more_messages_indicator'),
                                    {abs_positioned: true});
        loading_more_messages_indicator_showing = true;
        floating_recipient_bar.hide();
    }
};

exports.hide_loading_older = function () {
    if (loading_more_messages_indicator_showing) {
        loading.destroy_indicator($("#loading_more_messages_indicator"));
        loading_more_messages_indicator_showing = false;
    }
};

exports.hide_indicators = function () {
    exports.hide_loading_older();
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

    if (message_viewport.at_top()) {
        message_fetch.maybe_load_older_messages({
            msg_list: current_msg_list,
            show_loading: exports.show_loading_older,
            hide_loading: exports.hide_loading_older,
        });
    }

    // When the window scrolls, it may cause some messages to
    // enter the screen and become read.  Calling
    // unread_ops.process_visible will update necessary
    // data structures and DOM elements.
    setTimeout(unread_ops.process_visible, 0);
};

var scroll_timer;
function scroll_finish(opts) {
    actively_scrolling = true;
    clearTimeout(scroll_timer);

    function finish() {
        exports.scroll_finished(opts);
    }

    // TODO: consider removing the 100ms timeout here, since
    //       we are already on a 50ms throttle
    scroll_timer = setTimeout(finish, 100);
}

exports.initialize = function () {
    function on_scroll_callback(opts) {
        unread_ops.process_visible();
        scroll_finish({
            moving_down: opts.moving_down,
        });
    }

    message_viewport.scrolling.set_callback({
        throttle_ms: 50,
        callback: on_scroll_callback,
    });
};


return exports;

}());
if (typeof module !== 'undefined') {
    module.exports = message_scroll;
}
