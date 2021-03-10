"use strict";

const {strict: assert} = require("assert");

const {mock_esm, set_global, zrequire} = require("../zjsunit/namespace");
const {run_test} = require("../zjsunit/test");

mock_esm("../../static/js/resize", {
    resize_stream_filters_container: () => {},
});

const channel = mock_esm("../../static/js/channel");
const compose = mock_esm("../../static/js/compose");
const compose_actions = mock_esm("../../static/js/compose_actions");
const hashchange = mock_esm("../../static/js/hashchange");
const message_fetch = mock_esm("../../static/js/message_fetch");
const message_list = mock_esm("../../static/js/message_list", {
    set_narrowed(value) {
        message_list.narrowed = value;
    },
});
const message_scroll = mock_esm("../../static/js/message_scroll");
const message_view_header = mock_esm("../../static/js/message_view_header");
const notifications = mock_esm("../../static/js/notifications");
const search = mock_esm("../../static/js/search");
const stream_list = mock_esm("../../static/js/stream_list");
const top_left_corner = mock_esm("../../static/js/top_left_corner");
const typing_events = mock_esm("../../static/js/typing_events");
const ui_util = mock_esm("../../static/js/ui_util");
const unread_ops = mock_esm("../../static/js/unread_ops");
mock_esm("../../static/js/recent_topics", {
    hide: () => {},
    is_visible: () => {},
});
set_global("current_msg_list", {});
set_global("home_msg_list", {});
set_global("page_params", {});

//
// We have strange hacks in narrow.activate to sleep 0
// seconds.
set_global("setTimeout", (f, t) => {
    assert.equal(t, 0);
    f();
});

mock_esm("../../static/js/muting", {
    is_topic_muted: () => false,
});

const util = zrequire("util");
const narrow_state = zrequire("narrow_state");
const stream_data = zrequire("stream_data");
const narrow = zrequire("narrow");

const denmark = {
    subscribed: false,
    color: "blue",
    name: "Denmark",
    stream_id: 1,
    is_muted: true,
};
stream_data.add_sub(denmark);

function test_helper() {
    let events = [];

    function stub(module, func_name) {
        module[func_name] = () => {
            events.push([module, func_name]);
        };
    }

    stub(compose_actions, "on_narrow");
    stub(hashchange, "save_narrow");
    stub(message_scroll, "hide_indicators");
    stub(message_scroll, "show_loading_older");
    stub(message_scroll, "hide_top_of_narrow_notices");
    stub(notifications, "clear_compose_notifications");
    stub(notifications, "redraw_title");
    stub(search, "update_button_visibility");
    stub(stream_list, "handle_narrow_activated");
    stub(message_view_header, "initialize");
    stub(top_left_corner, "handle_narrow_activated");
    stub(typing_events, "render_notifications_for_narrow");
    stub(ui_util, "change_tab_to");
    stub(unread_ops, "process_visible");
    stub(compose, "update_closed_compose_buttons_for_stream");
    stub(compose, "update_closed_compose_buttons_for_private");

    return {
        clear: () => {
            events = [];
        },
        push_event: (event) => {
            events.push(event);
        },
        assert_events: (expected_events) => {
            assert.deepEqual(expected_events, events);
        },
    };
}

function stub_message_list() {
    message_list.MessageList = function (opts) {
        this.data = opts.data;
        this.view = {
            set_message_offset(offset) {
                this.offset = offset;
            },
        };

        return this;
    };

    message_list.MessageList.prototype = {
        get(msg_id) {
            return this.data.get(msg_id);
        },

        empty() {
            return this.data.empty();
        },

        select_id(msg_id) {
            this.selected_id = msg_id;
        },
    };
}

run_test("basics", () => {
    stub_message_list();

    const helper = test_helper();
    const terms = [{operator: "stream", operand: "Denmark"}];

    const selected_id = 1000;

    const selected_message = {
        id: selected_id,
        type: "stream",
        stream_id: denmark.stream_id,
        topic: "whatever",
    };

    const messages = [selected_message];

    const row = {
        length: 1,
        offset: () => ({top: 25}),
    };

    current_msg_list.selected_id = () => -1;
    current_msg_list.get_row = () => row;

    message_list.all = {
        all_messages: () => messages,
        get: (msg_id) => {
            assert.equal(msg_id, selected_id);
            return selected_message;
        },
        data: {
            fetch_status: {
                has_found_newest: () => true,
            },
        },
        empty: () => false,
        first: () => ({id: 900}),
        last: () => ({id: 1100}),
    };

    let cont;

    message_fetch.load_messages_for_narrow = (opts) => {
        cont = opts.cont;

        assert.deepEqual(opts, {
            cont: opts.cont,
            anchor: 1000,
        });
    };

    narrow.activate(terms, {
        then_select_id: selected_id,
    });

    assert.equal(message_list.narrowed.selected_id, selected_id);
    assert.equal(message_list.narrowed.view.offset, 25);
    assert.equal(narrow_state.narrowed_to_pms(), false);

    helper.assert_events([
        [notifications, "clear_compose_notifications"],
        [notifications, "redraw_title"],
        [message_scroll, "hide_top_of_narrow_notices"],
        [message_scroll, "hide_indicators"],
        [ui_util, "change_tab_to"],
        [unread_ops, "process_visible"],
        [hashchange, "save_narrow"],
        [compose, "update_closed_compose_buttons_for_stream"],
        [search, "update_button_visibility"],
        [compose_actions, "on_narrow"],
        [top_left_corner, "handle_narrow_activated"],
        [stream_list, "handle_narrow_activated"],
        [typing_events, "render_notifications_for_narrow"],
        [message_view_header, "initialize"],
    ]);

    current_msg_list.selected_id = () => -1;
    current_msg_list.get_row = () => row;
    util.sorted_ids = () => [];

    narrow.activate([{operator: "is", operand: "private"}], {
        then_select_id: selected_id,
    });

    assert.equal(narrow_state.narrowed_to_pms(), true);

    channel.post = (opts) => {
        assert.equal(opts.url, "/json/report/narrow_times");
        helper.push_event("report narrow times");
    };

    helper.clear();
    cont();
    helper.assert_events(["report narrow times"]);
});
