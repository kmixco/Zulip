var message_fetch = (function () {

var exports = {};

var consts = {
    backfill_idle_time: 10*1000,
    error_retry_time: 5000,
    backfill_batch_size: 1000,
    narrow_before: 50,
    narrow_after: 50,
    num_before_pointer: 200,
    num_after_pointer: 200,
    backward_batch_size: 100,
    catch_up_batch_size: 1000,
};

function process_result(data, opts) {
    var messages = data.messages;

    $('#connection-error').removeClass("show");

    if ((messages.length === 0) && (current_msg_list === message_list.narrowed) &&
        message_list.narrowed.empty()) {
        // Even after trying to load more messages, we have no
        // messages to display in this narrow.
        narrow.show_empty_narrow_message();
    }

    _.each(messages, message_store.set_message_booleans);
    messages = _.map(messages, message_store.add_message_metadata);

    // If we're loading more messages into the home view, save them to
    // the message_list.all as well, as the home_msg_list is reconstructed
    // from message_list.all.
    if (opts.msg_list === home_msg_list) {
        message_util.do_unread_count_updates(messages);
        message_util.add_messages(messages, message_list.all, {messages_are_new: false});
    }

    if (messages.length !== 0) {
        message_util.add_messages(messages, opts.msg_list, {messages_are_new: false});
    }

    activity.process_loaded_messages(messages);
    stream_list.update_streams_sidebar();
    pm_list.update_private_messages();

    if (opts.cont !== undefined) {
        opts.cont(data);
    }
}

function get_messages_success(data, opts) {
    if (opts.msg_list.narrowed && opts.msg_list !== current_msg_list) {
        // We unnarrowed before receiving new messages so
        // don't bother processing the newly arrived messages.
        return;
    }
    if (! data) {
        // The server occasionally returns no data during a
        // restart.  Ignore those responses and try again
        setTimeout(function () {
            exports.load_messages(opts);
        }, 0);
        return;
    }

    process_result(data, opts);
    resize.resize_bottom_whitespace();
}


exports.load_messages = function (opts) {
    var data = {anchor: opts.anchor,
                num_before: opts.num_before,
                num_after: opts.num_after};

    if (opts.msg_list.narrowed && narrow_state.active()) {
        var operators = narrow_state.public_operators();
        if (page_params.narrow !== undefined) {
            operators = operators.concat(page_params.narrow);
        }
        data.narrow = JSON.stringify(operators);
    }
    if (opts.msg_list === home_msg_list && page_params.narrow_stream !== undefined) {
        data.narrow = JSON.stringify(page_params.narrow);
    }
    if (opts.use_first_unread_anchor) {
        data.use_first_unread_anchor = true;
    }

    data.client_gravatar = true;

    channel.get({
        url:      '/json/messages',
        data:     data,
        idempotent: true,
        success: function (data) {
            get_messages_success(data, opts);
        },
        error: function (xhr) {
            if (opts.msg_list.narrowed && opts.msg_list !== current_msg_list) {
                // We unnarrowed before getting an error so don't
                // bother trying again or doing further processing.
                return;
            }
            if (xhr.status === 400) {
                // Bad request: We probably specified a narrow operator
                // for a nonexistent stream or something.  We shouldn't
                // retry or display a connection error.
                //
                // FIXME: Warn the user when this has happened?
                var data = {
                    messages: [],
                };
                process_result(data, opts);
                return;
            }

            // We might want to be more clever here
            $('#connection-error').addClass("show");
            setTimeout(function () {
                exports.load_messages(opts);
            }, consts.error_retry_time);
        },
    });
};

exports.load_messages_for_narrow = function (opts) {
    message_fetch.load_messages({
        anchor: opts.then_select_id.toFixed(),
        num_before: consts.narrow_before,
        num_after: consts.narrow_after,
        msg_list: message_list.narrowed,
        use_first_unread_anchor: opts.use_initial_narrow_pointer,
        cont: function () {
            // TODO: if we know we got all the messages for this
            // narrow, call message_list.narrow.fetch_status
            // to prevent more fetching
            message_scroll.hide_indicators();
            opts.cont();
        },
    });
};

exports.maybe_load_older_messages = function (opts) {
    // This function gets called when you scroll to the top
    // of your window, and you want to get messages older
    // than what the browers originally fetched.
    var msg_list = opts.msg_list;
    var oldest_message_id;
    if (!msg_list.fetch_status.can_load_older_messages()) {
        // We may already be loading old messages or already
        // got the oldest one.
        return;
    }
    opts.show_loading();
    msg_list.fetch_status.start_older_batch();
    if (msg_list.first() === undefined) {
        oldest_message_id = page_params.pointer;
    } else {
        oldest_message_id = msg_list.first().id;
    }

    var batch_size = consts.backward_batch_size;

    exports.load_messages({
        anchor: oldest_message_id.toFixed(),
        num_before: batch_size,
        num_after: 0,
        msg_list: msg_list,
        cont: function (data) {
            opts.hide_loading();
            msg_list.fetch_status.finish_older_batch({
                found_oldest: data.found_oldest,
            });
        },
    });
};

exports.initialize = function () {
    // get the initial message list
    function load_more(data) {
        var messages = data.messages;

        // If we received the initially selected message, select it on the client side,
        // but not if the user has already selected another one during load.
        //
        // We fall back to the closest selected id, as the user may have removed
        // a stream from the home before already
        if (home_msg_list.selected_id() === -1 && !home_msg_list.empty()) {
            home_msg_list.select_id(page_params.pointer,
                                    {then_scroll: true, use_closest: true,
                                     target_scroll_offset: page_params.initial_offset});
        }

        // catch the user up
        if (messages.length !== 0) {
            var latest_id = messages[messages.length-1].id;
            if (latest_id < page_params.max_message_id) {
                exports.load_messages({
                    anchor: latest_id.toFixed(),
                    num_before: 0,
                    num_after: consts.catch_up_batch_size,
                    msg_list: home_msg_list,
                    cont: load_more,
                });
                return;
            }
        }

        server_events.home_view_loaded();

        // backfill more messages after the user is idle
        $(document).idle({idle: consts.backfill_idle_time,
                          onIdle: function () {
                              var first_id = message_list.all.first().id;
                              exports.load_messages({
                                  anchor: first_id,
                                  num_before: consts.backfill_batch_size,
                                  num_after: 0,
                                  msg_list: home_msg_list,
                              });
                          }});
    }

    if (page_params.have_initial_messages) {
        exports.load_messages({
            anchor: page_params.pointer,
            num_before: consts.num_before_pointer,
            num_after: consts.num_after_pointer,
            msg_list: home_msg_list,
            cont: load_more,
        });
    } else {
        server_events.home_view_loaded();
    }
};

return exports;

}());
if (typeof module !== 'undefined') {
    module.exports = message_fetch;
}
