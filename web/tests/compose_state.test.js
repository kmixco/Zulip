"use strict";

const {strict: assert} = require("assert");

const {mock_esm, zrequire} = require("./lib/namespace");
const {run_test} = require("./lib/test");

const compose_pm_pill = mock_esm("../src/compose_pm_pill");

const compose_state = zrequire("compose_state");

run_test("private_message_recipient", () => {
    let emails;
    compose_pm_pill.compose_pm_pill = {
        get_emails: () => emails,
        set_from_emails(value) {
            emails = value;
        },
    };

    compose_state.private_message_recipient("fred@fred.org");
    assert.equal(compose_state.private_message_recipient(), "fred@fred.org");
});

run_test("has_full_recipient", () => {
    let emails;
    compose_pm_pill.compose_pm_pill = {
        get_emails: () => emails,
        set_from_emails(value) {
            emails = value;
        },
    };

    compose_state.set_message_type("stream");
    compose_state.set_stream_name("");
    compose_state.topic("");
    assert.equal(compose_state.has_full_recipient(), false);

    compose_state.topic("foo");
    assert.equal(compose_state.has_full_recipient(), false);

    compose_state.set_stream_name("bar");
    assert.equal(compose_state.has_full_recipient(), true);

    compose_state.set_message_type("private");
    compose_state.private_message_recipient("");
    assert.equal(compose_state.has_full_recipient(), false);

    compose_state.private_message_recipient("foo@zulip.com");
    assert.equal(compose_state.has_full_recipient(), true);
});
