// Read https://zulip.readthedocs.io/en/latest/hashchange-system.html
var reload = (function () {

var exports = {};

var reload_in_progress = false;
var reload_pending = false;

exports.is_pending = function () {
    return reload_pending;
};

exports.is_in_progress = function () {
    return reload_in_progress;
};

function preserve_state(send_after_reload, save_pointer, save_narrow, save_compose) {
    if (send_after_reload === undefined) {
        send_after_reload = 0;
    }
    var url = "#reload:send_after_reload=" + Number(send_after_reload);
    url += "+csrf_token=" + encodeURIComponent(csrf_token);

    if (save_compose) {
        if (compose_state.composing() === 'stream') {
            url += "+msg_type=stream";
            url += "+stream=" + encodeURIComponent(compose_state.stream_name());
            url += "+subject=" + encodeURIComponent(compose_state.subject());
        } else if (compose_state.composing() === 'private') {
            url += "+msg_type=private";
            url += "+recipient=" + encodeURIComponent(compose_state.recipient());
        }

        if (compose_state.composing()) {
            url += "+msg=" + encodeURIComponent(compose_state.message_content());
        }
    }

    if (save_pointer) {
        var pointer = home_msg_list.selected_id();
        if (pointer !== -1) {
            url += "+pointer=" + pointer;
        }
    }

    if (save_narrow) {
        var row = home_msg_list.selected_row();
        if (!narrow.active()) {
            if (row.length > 0) {
                url += "+offset=" + row.offset().top;
            }
        } else {
            url += "+offset=" + home_msg_list.pre_narrow_offset;

            var narrow_pointer = message_list.narrowed.selected_id();
            if (narrow_pointer !== -1) {
                url += "+narrow_pointer=" + narrow_pointer;
            }
            var narrow_row = message_list.narrowed.selected_row();
            if (narrow_row.length > 0) {
                url += "+narrow_offset=" + narrow_row.offset().top;
            }
        }
    }

    var oldhash = window.location.hash;
    if (oldhash.length !== 0 && oldhash[0] === '#') {
        oldhash = oldhash.slice(1);
    }
    url += "+oldhash=" + encodeURIComponent(oldhash);

    // To protect the browser against CSRF type attacks, the reload
    // logic uses a random token (to distinct this browser from
    // others) which is passed via the URL to the browser (post
    // reloading).  The token is a key into local storage, where we
    // marshall and store the URL.
    //
    // TODO: Remove the now-unnecessary URL-encoding logic above and
    // just pass the actual data structures through local storage.
    var token = util.random_int(0, 1024*1024*1024*1024);
    var ls = localstorage();

    ls.set("reload:" + token, url);
    window.location.replace("#reload:" + token);
}


// Check if we're doing a compose-preserving reload.  This must be
// done before the first call to get_events
exports.initialize = function reload__initialize() {
    var location = window.location.toString();
    var hash_fragment = location.substring(location.indexOf('#') + 1);

    // hash_fragment should be e.g. `reload:12345123412312`
    if (hash_fragment.search("reload:") !== 0) {
        return;
    }

    // Using the token, recover the saved pre-reload data from local
    // storage.  Afterwards, we clear the reload entry from local
    // storage to avoid a local storage space leak.
    var ls = localstorage();
    var fragment = ls.get(hash_fragment);
    if (fragment === undefined) {
        blueslip.error("Invalid hash change reload token");
        return;
    }
    ls.remove(hash_fragment);

    fragment = fragment.replace(/^reload:/, "");
    var keyvals = fragment.split("+");
    var vars = {};
    _.each(keyvals, function (str) {
        var pair = str.split("=");
        vars[pair[0]] = decodeURIComponent(pair[1]);
    });

    if (vars.msg !== undefined) {
        var send_now = parseInt(vars.send_after_reload, 10);

        // TODO: preserve focus
        compose_actions.start(vars.msg_type, {stream: vars.stream || '',
                                      subject: vars.subject || '',
                                      private_message_recipient: vars.recipient || '',
                                      content: vars.msg || ''});
        if (send_now) {
            compose.finish();
        }
    }

    var pointer = parseInt(vars.pointer, 10);

    if (pointer) {
        page_params.orig_initial_pointer = page_params.initial_pointer;
        page_params.initial_pointer = pointer;
    }
    var offset = parseInt(vars.offset, 10);
    if (offset) {
        page_params.initial_offset = offset;
    }

    var narrow_pointer = parseInt(vars.narrow_pointer, 10);
    if (narrow_pointer) {
        page_params.initial_narrow_pointer = narrow_pointer;
    }
    var narrow_offset = parseInt(vars.narrow_offset, 10);
    if (narrow_offset) {
        page_params.initial_narrow_offset = narrow_offset;
    }

    activity.new_user_input = false;
    hashchange.changehash(vars.oldhash);
};

function do_reload_app(send_after_reload, save_pointer, save_narrow, save_compose, message) {
    if (reload_in_progress) { return; }

    // TODO: we should completely disable the UI here
    if (save_pointer || save_narrow || save_compose) {
        try {
            preserve_state(send_after_reload, save_pointer, save_narrow, save_compose);
        } catch (ex) {
            blueslip.error('Failed to preserve state',
                           undefined, ex.stack);
        }
    }

    if (message === undefined) {
        message = "Reloading";
    }

    // TODO: We need a better API for showing messages.
    ui_report.message(message, $("#reloading-application"));
    blueslip.log('Starting server requested page reload');
    reload_in_progress = true;

    try {
        server_events.cleanup_event_queue();
    } catch (ex) {
        blueslip.error('Failed to cleanup before reloading',
                       undefined, ex.stack);
    }

    window.location.reload(true);
}

exports.initiate = function (options) {
    options = _.defaults({}, options, {
        immediate: false,
        save_pointer: true,
        save_narrow: true,
        save_compose: true,
        send_after_reload: false,
    });

    if (options.save_pointer === undefined ||
        options.save_narrow === undefined ||
        options.save_compose === undefined) {
        blueslip.error("reload.initiate() called without explicit save options.");
    }

    if (options.immediate) {
        do_reload_app(options.send_after_reload,
                      options.save_pointer,
                      options.save_narrow,
                      options.save_compose,
                      options.message);
    }

    if (reload_pending) {
        return;
    }
    reload_pending = true;

    // If the user is composing a message, reload if they become idle
    // while composing.  If they finish or cancel the compose, wait
    // until they're idle again
    var idle_control;
    var unconditional_timeout = 1000*60*30 + util.random_int(0, 1000*60*5);
    var composing_timeout     = 1000*60*5  + util.random_int(0, 1000*60);
    var home_timeout          = 1000*60    + util.random_int(0, 1000*60);
    var compose_done_handler;
    var compose_started_handler;

    function reload_from_idle() {
        do_reload_app(false,
                      options.save_pointer,
                      options.save_narrow,
                      options.save_compose,
                      options.message);
    }

    // Make sure we always do a reload eventually
    setTimeout(reload_from_idle, unconditional_timeout);

    compose_done_handler = function () {
        idle_control.cancel();
        idle_control = $(document).idle({idle: home_timeout,
                                         onIdle: reload_from_idle});
        $(document).off('compose_canceled.zulip compose_finished.zulip',
                        compose_done_handler);
        $(document).on('compose_started.zulip', compose_started_handler);
    };
    compose_started_handler = function () {
        idle_control.cancel();
        idle_control = $(document).idle({idle: composing_timeout,
                                         onIdle: reload_from_idle});
        $(document).off('compose_started.zulip', compose_started_handler);
        $(document).on('compose_canceled.zulip compose_finished.zulip',
                       compose_done_handler);
    };

    if (compose_state.composing()) {
        idle_control = $(document).idle({idle: composing_timeout,
                                         onIdle: reload_from_idle});
        $(document).on('compose_canceled.zulip compose_finished.zulip',
                       compose_done_handler);
    } else {
        idle_control = $(document).idle({idle: home_timeout,
                                         onIdle: reload_from_idle});
        $(document).on('compose_started.zulip', compose_started_handler);
    }
};

window.addEventListener('beforeunload', function () {
    // When navigating away from the page do not try to reload.
    // The polling get_events call will fail after we delete the event queue.
    // When that happens we reload the page to correct the problem. If this
    // happens before the navigation is complete the user is kept captive at
    // zulip.
    reload_in_progress = true;
});


return exports;
}());

if (typeof module !== 'undefined') {
    module.exports = reload;
}
