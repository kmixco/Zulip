"use strict";

const {strict: assert} = require("assert");

const {mock_esm, zrequire} = require("../zjsunit/namespace");
const {run_test} = require("../zjsunit/test");
const $ = require("../zjsunit/zjquery");

const narrow_state = mock_esm("../../static/js/narrow_state");
const unread = mock_esm("../../static/js/unread");

mock_esm("../../static/js/user_status", {
    is_away: () => false,
    get_status_emoji: () => ({
        emoji_code: 20,
    }),
});

const people = zrequire("people");
const pm_conversations = zrequire("pm_conversations");
const pm_list_data = zrequire("pm_list_data");
const pm_list = zrequire("pm_list");

const alice = {
    email: "alice@zulip.com",
    user_id: 101,
    full_name: "Alice",
};
const bob = {
    email: "bob@zulip.com",
    user_id: 102,
    full_name: "Bob",
};
const me = {
    email: "me@zulip.com",
    user_id: 103,
    full_name: "Me Myself",
};
const bot_test = {
    email: "outgoingwebhook@zulip.com",
    user_id: 314,
    full_name: "Outgoing webhook",
    is_admin: false,
    is_bot: true,
};
people.add_active_user(alice);
people.add_active_user(bob);
people.add_active_user(me);
people.add_active_user(bot_test);
people.initialize_current_user(me.user_id);

function test(label, f) {
    run_test(label, ({override, override_rewire}) => {
        pm_conversations.clear_for_testing();
        f({override, override_rewire});
    });
}

test("get_convos", ({override}) => {
    const timestamp = 0;
    pm_conversations.recent.insert([101, 102], timestamp);
    pm_conversations.recent.insert([103], timestamp);
    let num_unread_for_person = 1;
    override(unread, "num_unread_for_person", () => num_unread_for_person);

    override(narrow_state, "filter", () => {});

    const expected_data = [
        {
            is_active: false,
            is_group: false,
            is_zero: false,
            recipients: "Me Myself",
            unread: 1,
            url: "#narrow/pm-with/103-me",
            user_circle_class: "user_circle_empty",
            user_ids_string: "103",
            status_emoji_info: {
                emoji_code: 20,
            },
        },
        {
            recipients: "Alice, Bob",
            user_ids_string: "101,102",
            unread: 1,
            is_zero: false,
            is_active: false,
            url: "#narrow/pm-with/101,102-group",
            user_circle_class: undefined,
            is_group: true,
            status_emoji_info: undefined,
        },
    ];

    let pm_data = pm_list_data.get_convos();
    assert.deepEqual(pm_data, expected_data);

    num_unread_for_person = 0;

    pm_data = pm_list_data.get_convos();
    expected_data[0].unread = 0;
    expected_data[0].is_zero = true;
    expected_data[1].unread = 0;
    expected_data[1].is_zero = true;
    assert.deepEqual(pm_data, expected_data);

    pm_data = pm_list_data.get_convos();
    assert.deepEqual(pm_data, expected_data);
});

test("get_convos bot", ({override}) => {
    const timestamp = 0;
    pm_conversations.recent.insert([101, 102], timestamp);
    pm_conversations.recent.insert([bot_test.user_id], timestamp);

    override(unread, "num_unread_for_person", () => 1);

    override(narrow_state, "filter", () => {});

    const expected_data = [
        {
            recipients: "Outgoing webhook",
            user_ids_string: "314",
            unread: 1,
            is_zero: false,
            is_active: false,
            url: "#narrow/pm-with/314-outgoingwebhook",
            status_emoji_info: undefined,
            user_circle_class: "user_circle_green",
            is_group: false,
        },
        {
            recipients: "Alice, Bob",
            user_ids_string: "101,102",
            unread: 1,
            is_zero: false,
            is_active: false,
            url: "#narrow/pm-with/101,102-group",
            user_circle_class: undefined,
            status_emoji_info: undefined,
            is_group: true,
        },
    ];

    const pm_data = pm_list_data.get_convos();
    assert.deepEqual(pm_data, expected_data);
});

test("update_dom_with_unread_counts", ({override}) => {
    let counts;

    override(narrow_state, "active", () => true);

    const total_count = $.create("total-count-stub");
    const private_li = $(".top_left_private_messages .private_messages_header");
    private_li.set_find_results(".unread_count", total_count);

    counts = {
        private_message_count: 10,
    };

    pm_list.update_dom_with_unread_counts(counts);
    assert.equal(total_count.text(), "10");
    assert.ok(total_count.visible());

    counts = {
        private_message_count: 0,
    };

    pm_list.update_dom_with_unread_counts(counts);
    assert.equal(total_count.text(), "");
    assert.ok(!total_count.visible());
});

test("get_active_user_ids_string", ({override}) => {
    let active_filter;

    override(narrow_state, "filter", () => active_filter);

    assert.equal(pm_list_data.get_active_user_ids_string(), undefined);

    function set_filter_result(emails) {
        active_filter = {
            operands: (operand) => {
                assert.equal(operand, "pm-with");
                return emails;
            },
        };
    }

    set_filter_result([]);
    assert.equal(pm_list_data.get_active_user_ids_string(), undefined);

    set_filter_result(["bob@zulip.com,alice@zulip.com"]);
    assert.equal(pm_list_data.get_active_user_ids_string(), "101,102");
});

function private_filter() {
    return {
        operands: (operand) => {
            assert.equal(operand, "is");
            return ["private", "starred"];
        },
    };
}

test("is_all_privates", ({override}) => {
    let filter;
    override(narrow_state, "filter", () => filter);

    filter = undefined;
    assert.equal(pm_list_data.is_all_privates(), false);

    filter = private_filter();
    assert.equal(pm_list_data.is_all_privates(), true);
});
