"use strict";

const {strict: assert} = require("assert");

const {$t} = require("./lib/i18n");
const {mock_esm, set_global, zrequire} = require("./lib/namespace");
const {run_test, noop} = require("./lib/test");

const dropdown_widget = mock_esm("../src/dropdown_widget", {
    DataTypes: {NUMBER: "number", STRING: "string"},
});
dropdown_widget.DropdownWidget = function DropdownWidget() {
    this.setup = noop;
    this.render = noop;
};

set_global("page_params", {
    is_spectator: false,
});

const params = {
    saved_replies: [
        {
            id: 1,
            title: "Test saved reply",
            content: "Test content",
            date_created: 128374878,
        },
    ],
};

const people = zrequire("people");
const saved_replies = zrequire("saved_replies");
const saved_replies_ui = zrequire("saved_replies_ui");

people.add_active_user({
    email: "tester@zulip.com",
    full_name: "Tester von Tester",
    user_id: 42,
});

people.initialize_current_user(42);

saved_replies_ui.initialize(params);

run_test("add_saved_reply", () => {
    assert.deepEqual(saved_replies.get_saved_replies(), params.saved_replies);

    const saved_reply = {
        id: 2,
        title: "New saved reply",
        content: "Test content",
        date_created: 128374878,
    };
    saved_replies.add_saved_reply(saved_reply);

    const my_saved_replies = saved_replies.get_saved_replies();
    assert.equal(my_saved_replies.length, 2);
    assert.deepEqual(my_saved_replies[0], saved_reply);
});

run_test("options for dropdown widget", () => {
    const saved_reply = {
        id: 3,
        title: "Another saved reply",
        content: "Test content",
        date_created: 128374876,
    };
    saved_replies.add_saved_reply(saved_reply);

    assert.deepEqual(saved_replies.get_options_for_dropdown_widget(), [
        {
            unique_id: -1,
            name: $t({defaultMessage: "Add a new saved reply"}),
            description: "",
            bold_current_selection: true,
            has_delete_icon: false,
        },
        {
            unique_id: 3,
            name: "Another saved reply",
            description: "Test content",
            bold_current_selection: true,
            has_delete_icon: true,
        },
        {
            unique_id: 2,
            name: "New saved reply",
            description: "Test content",
            bold_current_selection: true,
            has_delete_icon: true,
        },
        {
            unique_id: 1,
            name: "Test saved reply",
            description: "Test content",
            bold_current_selection: true,
            has_delete_icon: true,
        },
    ]);
});

run_test("remove_saved_reply", () => {
    let my_saved_replies = saved_replies.get_saved_replies();
    assert.equal(my_saved_replies.length, 3);
    assert.equal(my_saved_replies[0].id, 3);
    saved_replies.remove_saved_reply(params.saved_replies[0].id);

    my_saved_replies = saved_replies.get_saved_replies();
    assert.equal(my_saved_replies.length, 2);
    assert.equal(my_saved_replies[0].id, 2);
});
