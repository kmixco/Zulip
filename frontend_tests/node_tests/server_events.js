"use strict";

const {strict: assert} = require("assert");

const {mock_module, set_global, use} = require("../zjsunit/namespace");
const {run_test} = require("../zjsunit/test");

const noop = () => {};

set_global("document", {
    to_$() {
        return {
            trigger() {},
        };
    },
});
set_global("addEventListener", noop);

const channel = mock_module("channel", {});
set_global("home_msg_list", {
    select_id: noop,
    selected_id() {
        return 1;
    },
});
set_global("page_params", {test_suite: false});
mock_module("reload_state", {
    is_in_progress() {
        return false;
    },
});

// we also directly write to pointer
set_global("pointer", {});

mock_module("ui_report", {
    hide_error() {
        return false;
    },
    show_error() {
        return false;
    },
});

mock_module("stream_events", {
    update_property() {
        throw new Error("subs update error");
    },
});

const message_events = mock_module("message_events", {
    insert_new_messages() {
        throw new Error("insert error");
    },
    update_messages() {
        throw new Error("update error");
    },
});

const {server_events} = use(
    "fold_dict",
    "echo",
    "server_events_dispatch",
    "sent_messages",
    "message_store",
    "stream_data",
    "server_events",
);

server_events.home_view_loaded();

run_test("message_event", (override) => {
    const event = {
        type: "message",
        message: {
            content: "hello",
        },
        flags: [],
    };

    let inserted;
    override(message_events, "insert_new_messages", (messages) => {
        assert.equal(messages[0].content, event.message.content);
        inserted = true;
    });

    server_events._get_events_success([event]);
    assert(inserted);
});

// Start blueslip tests here

const setup = () => {
    server_events.home_view_loaded();
};

run_test("event_dispatch_error", () => {
    setup();

    const data = {events: [{type: "stream", op: "update", id: 1, other: "thing"}]};
    channel.get = (options) => {
        options.success(data);
    };

    blueslip.expect("error", "Failed to process an event\nsubs update error");

    server_events.restart_get_events();

    const logs = blueslip.get_test_logs("error");
    assert.equal(logs.length, 1);
    assert.equal(logs[0].more_info.event.type, "stream");
    assert.equal(logs[0].more_info.event.op, "update");
    assert.equal(logs[0].more_info.event.id, 1);
    assert.equal(logs[0].more_info.other, undefined);
});

run_test("event_new_message_error", () => {
    setup();

    const data = {events: [{type: "message", id: 1, other: "thing", message: {}}]};
    channel.get = (options) => {
        options.success(data);
    };

    blueslip.expect("error", "Failed to insert new messages\ninsert error");

    server_events.restart_get_events();

    const logs = blueslip.get_test_logs("error");
    assert.equal(logs.length, 1);
    assert.equal(logs[0].more_info, undefined);
});

run_test("event_edit_message_error", () => {
    setup();
    const data = {events: [{type: "update_message", id: 1, other: "thing"}]};
    channel.get = (options) => {
        options.success(data);
    };
    blueslip.expect("error", "Failed to update messages\nupdate error");

    server_events.restart_get_events();

    const logs = blueslip.get_test_logs("error");
    assert.equal(logs.length, 1);
    assert.equal(logs[0].more_info, undefined);
});
