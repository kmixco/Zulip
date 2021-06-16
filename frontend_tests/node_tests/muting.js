"use strict";

const {strict: assert} = require("assert");

const {zrequire} = require("../zjsunit/namespace");
const {run_test} = require("../zjsunit/test");
const blueslip = require("../zjsunit/zblueslip");
const {page_params} = require("../zjsunit/zpage_params");

const muting = zrequire("muting");
const stream_data = zrequire("stream_data");

const design = {
    stream_id: 100,
    name: "design",
};

const devel = {
    stream_id: 101,
    name: "devel",
};

const office = {
    stream_id: 102,
    name: "office",
};

const social = {
    stream_id: 103,
    name: "social",
};

const unknown = {
    stream_id: 999,
    name: "whatever",
};

stream_data.add_sub(design);
stream_data.add_sub(devel);
stream_data.add_sub(office);
stream_data.add_sub(social);

function test(label, f) {
    run_test(label, ({override}) => {
        muting.set_muted_topics([]);
        muting.set_muted_users([]);
        f({override});
    });
}

test("edge_cases", () => {
    // private messages
    assert.ok(!muting.is_topic_muted(undefined, undefined));

    // invalid user
    assert.ok(!muting.is_user_muted(undefined));
});

test("add_and_remove_mutes", () => {
    assert.ok(!muting.is_topic_muted(devel.stream_id, "java"));
    muting.add_muted_topic(devel.stream_id, "java");
    assert.ok(muting.is_topic_muted(devel.stream_id, "java"));

    // test idempotentcy
    muting.add_muted_topic(devel.stream_id, "java");
    assert.ok(muting.is_topic_muted(devel.stream_id, "java"));

    muting.remove_muted_topic(devel.stream_id, "java");
    assert.ok(!muting.is_topic_muted(devel.stream_id, "java"));

    // test idempotentcy
    muting.remove_muted_topic(devel.stream_id, "java");
    assert.ok(!muting.is_topic_muted(devel.stream_id, "java"));

    // test unknown stream is harmless too
    muting.remove_muted_topic(unknown.stream_id, "java");
    assert.ok(!muting.is_topic_muted(unknown.stream_id, "java"));

    assert.ok(!muting.is_user_muted(1));
    muting.add_muted_user(1);
    assert.ok(muting.is_user_muted(1));

    // test idempotentcy
    muting.add_muted_user(1);
    assert.ok(muting.is_user_muted(1));

    muting.remove_muted_user(1);
    assert.ok(!muting.is_user_muted(1));

    // test idempotentcy
    muting.remove_muted_user(1);
    assert.ok(!muting.is_user_muted(1));
});

test("get_unmuted_users", () => {
    const hamlet = {
        user_id: 1,
        full_name: "King Hamlet",
    };
    const cordelia = {
        user_id: 2,
        full_name: "Cordelia, Lear's Daughter",
    };
    const othello = {
        user_id: 3,
        full_name: "Othello, Moor of Venice",
    };

    muting.add_muted_user(hamlet.user_id);
    muting.add_muted_user(cordelia.user_id);

    assert.deepEqual(
        muting.filter_muted_user_ids([hamlet.user_id, cordelia.user_id, othello.user_id]),
        [othello.user_id],
    );
    assert.deepEqual(muting.filter_muted_users([hamlet, cordelia, othello]), [othello]);
});

test("get_mutes", () => {
    assert.deepEqual(muting.get_muted_topics(), []);
    muting.add_muted_topic(office.stream_id, "gossip", 1577836800);
    muting.add_muted_topic(devel.stream_id, "java", 1577836700);
    const muted_topics = muting.get_muted_topics().sort((a, b) => a.date_muted - b.date_muted);

    assert.deepEqual(muted_topics, [
        {
            date_muted: 1577836700000,
            date_muted_str: "Dec\u00A031,\u00A02019",
            stream: devel.name,
            stream_id: devel.stream_id,
            topic: "java",
        },
        {
            date_muted: 1577836800000,
            date_muted_str: "Jan\u00A001,\u00A02020",
            stream: office.name,
            stream_id: office.stream_id,
            topic: "gossip",
        },
    ]);

    assert.deepEqual(muting.get_muted_users(), []);
    muting.add_muted_user(6, 1577836800);
    muting.add_muted_user(4, 1577836800);
    const muted_users = muting.get_muted_users().sort((a, b) => a.date_muted - b.date_muted);
    assert.deepEqual(muted_users, [
        {
            date_muted: 1577836800000,
            date_muted_str: "Jan\u00A001,\u00A02020",
            id: 6,
        },
        {
            date_muted: 1577836800000,
            date_muted_str: "Jan\u00A001,\u00A02020",
            id: 4,
        },
    ]);
});

test("unknown streams", () => {
    blueslip.expect("warn", "Unknown stream in set_muted_topics: BOGUS STREAM");

    page_params.muted_topics = [
        ["social", "breakfast", 1577836800],
        ["design", "typography", 1577836800],
        ["BOGUS STREAM", "whatever", 1577836800],
    ];
    page_params.muted_users = [
        {id: 3, timestamp: 1577836800},
        {id: 2, timestamp: 1577836800},
    ];
    muting.initialize();

    assert.deepEqual(muting.get_muted_topics().sort(), [
        {
            date_muted: 1577836800000,
            date_muted_str: "Jan\u00A001,\u00A02020",
            stream: social.name,
            stream_id: social.stream_id,
            topic: "breakfast",
        },
        {
            date_muted: 1577836800000,
            date_muted_str: "Jan\u00A001,\u00A02020",
            stream: design.name,
            stream_id: design.stream_id,
            topic: "typography",
        },
    ]);

    assert.deepEqual(muting.get_muted_users().sort(), [
        {
            date_muted: 1577836800000,
            date_muted_str: "Jan\u00A001,\u00A02020",
            id: 3,
        },
        {
            date_muted: 1577836800000,
            date_muted_str: "Jan\u00A001,\u00A02020",
            id: 2,
        },
    ]);
});

test("case_insensitivity", () => {
    muting.set_muted_topics([]);
    assert.ok(!muting.is_topic_muted(social.stream_id, "breakfast"));
    muting.set_muted_topics([["SOCial", "breakfast"]]);
    assert.ok(muting.is_topic_muted(social.stream_id, "breakfast"));
    assert.ok(muting.is_topic_muted(social.stream_id, "breakFAST"));
});
