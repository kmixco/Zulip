var muting_ui = (function () {

var exports = {};

function timestamp_ms() {
    return (new Date()).getTime();
}

var last_topic_update = 0;

exports.rerender = function () {
    // Note: We tend to optimistically rerender muting preferences before
    // the back end actually acknowledges the mute.  This gives a more
    // immediate feel to the user, and if the back end fails temporarily,
    // re-doing a mute or unmute is a pretty recoverable thing.

    stream_list.update_streams_sidebar();
    if (current_msg_list.muting_enabled) {
        current_msg_list.update_muting_and_rerender();
    }
    if (current_msg_list !== home_msg_list) {
        home_msg_list.update_muting_and_rerender();
    }
};

exports.build_feedback_widget = function () {
    var self = {};

    var meta = {
        hide_me_time: null,
        alert_hover_state: false,
        $container: null,
    };
    var animate = {
        fadeOut: function () {
            if (meta.$container) {
                meta.$container.fadeOut(500).removeClass("show");
            }
        },
        fadeIn: function () {
            if (meta.$container) {
                meta.$container.fadeIn(500).addClass("show");
            }
        },
    };
    setInterval(function () {
        if (meta.hide_me_time < new Date().getTime() && !meta.alert_hover_state) {
            animate.fadeOut();
        }
    }, 100);

    self.show = function (opts) {
        if (!opts.populate) {
            blueslip.error('programmer needs to supply populate callback.');
            return;
        }

        meta.undo = opts.on_undo;

        if (!meta.$container) {
            meta.$container = $("#feedback_container");

            meta.$container.find('.exit-me').click(function () {
                animate.fadeOut();
            });

            meta.$container.find(".feedback_undo").click(function () {
                if (meta.undo) {
                    meta.undo();
                }
                animate.fadeOut();
            });
        }

        // add a four second delay before closing up.
        meta.hide_me_time = new Date().getTime() + 4000;

        meta.$container.find('.feedback_title').text(opts.title_text);
        meta.$container.find('.feedback_undo').text(opts.undo_button_text);
        opts.populate(meta.$container.find('.feedback_content'));

        animate.fadeIn();

        // if the user mouses over the notification, don't hide it.
        meta.$container.mouseenter(function () {
            meta.alert_hover_state = true;
        });

        // once the user's mouse leaves the notification, restart the countdown.
        meta.$container.mouseleave(function () {
            meta.alert_hover_state = false;
            // add at least 2000ms but if more than that exists just keep the
            // current amount.
            meta.hide_me_time = Math.max(meta.hide_me_time, new Date().getTime() + 2000);
        });
    };

    self.dismiss = function () {
        var $container = $("#feedback_container");
        if ($container) {
            $container.fadeOut(500).removeClass("show");
        }
    };

    return self;
};

exports.notify_widget = exports.build_feedback_widget();

exports.persist_mute = function (stream_id, topic_name) {
    var data = {
        stream_id: stream_id,
        topic: topic_name,
        op: 'add',
    };
    last_topic_update = timestamp_ms();
    channel.patch({
        url: '/json/users/me/subscriptions/muted_topics',
        idempotent: true,
        data: data,
    });
};

exports.persist_unmute = function (stream_id, topic_name) {
    var data = {
        stream_id: stream_id,
        topic: topic_name,
        op: 'remove',
    };
    last_topic_update = timestamp_ms();
    channel.patch({
        url: '/json/users/me/subscriptions/muted_topics',
        idempotent: true,
        data: data,
    });
};

exports.handle_updates = function (muted_topics) {
    if (timestamp_ms() < last_topic_update + 1000) {
        // This topic update is either the one that we just rendered, or,
        // much less likely, it's coming from another device and would probably
        // be overwriting this device's preferences with stale data.
        return;
    }

    exports.update_muted_topics(muted_topics);
    exports.rerender();
};

exports.update_muted_topics = function (muted_topics) {
    muting.set_muted_topics(muted_topics);
    unread_ui.update_unread_counts();
};

exports.set_up_muted_topics_ui = function (muted_topics) {
    var muted_topics_table = $("#muted_topics_table tbody");
    muted_topics_table.empty();
    _.each(muted_topics, function (tup) {
        var stream_id = tup[0];
        var topic = tup[1];

        var stream = stream_data.maybe_get_stream_name(stream_id);

        if (!stream) {
            blueslip.warn('Unknown stream_id in set_up_muted_topics_ui: ' + stream_id);
            return;
        }

        var template_data = {
            stream: stream,
            stream_id: stream_id,
            topic: topic,
        };

        var row = templates.render('muted_topic_ui_row', template_data);
        muted_topics_table.append(row);
    });
};

exports.mute = function (stream_id, topic) {
    var stream_name = stream_data.maybe_get_stream_name(stream_id);

    stream_popover.hide_topic_popover();
    muting.add_muted_topic(stream_id, topic);
    unread_ui.update_unread_counts();
    exports.rerender();
    exports.persist_mute(stream_id, topic);
    exports.notify_widget.show({
        populate: function (container) {
            var rendered_html = templates.render('topic_muted');
            container.html(rendered_html);
            container.find(".stream").text(stream_name);
            container.find(".topic").text(topic);
        },
        on_undo: function () {
            exports.unmute(stream_id, topic);
        },
        title_text: i18n.t("Topic muted"),
        undo_button_text: i18n.t("Unmute"),
    });
    exports.set_up_muted_topics_ui(muting.get_muted_topics());
};

exports.unmute = function (stream_id, topic) {
    // we don't run a unmute_notify function because it isn't an issue as much
    // if someone accidentally unmutes a stream rather than if they mute it
    // and miss out on info.
    stream_popover.hide_topic_popover();
    muting.remove_muted_topic(stream_id, topic);
    unread_ui.update_unread_counts();
    exports.rerender();
    exports.persist_unmute(stream_id, topic);
    exports.set_up_muted_topics_ui(muting.get_muted_topics());
    exports.notify_widget.dismiss();
};

exports.toggle_mute = function (message) {
    var stream_id = message.stream_id;
    var topic = util.get_message_topic(message);

    if (muting.is_topic_muted(stream_id, topic)) {
        exports.unmute(stream_id, topic);
    } else if (message.type === 'stream') {
        exports.mute(stream_id, topic);
    }
};

return exports;
}());

if (typeof module !== 'undefined') {
    module.exports = muting_ui;
}
window.muting_ui = muting_ui;
