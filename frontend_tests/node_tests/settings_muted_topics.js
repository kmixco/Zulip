"use strict";

const {strict: assert} = require("assert");

const {mock_cjs, mock_esm, zrequire} = require("../zjsunit/namespace");
const {run_test} = require("../zjsunit/test");
const $ = require("../zjsunit/zjquery");

mock_cjs("jquery", $);
const muting_ui = mock_esm("../../static/js/muting_ui");

const settings_muted_topics = zrequire("settings_muted_topics");
const stream_data = zrequire("stream_data");
const muting = zrequire("muting");

const noop = () => {};

const frontend = {
    stream_id: 101,
    name: "frontend",
};
stream_data.add_sub(frontend);

run_test("settings", (override) => {
    muting.add_muted_topic(frontend.stream_id, "js", 1577836800);
    let populate_list_called = false;
    override(settings_muted_topics, "populate_list", () => {
        const opts = muting.get_muted_topics();
        assert.deepEqual(opts, [
            {
                date_muted: 1577836800000,
                date_muted_str: "Jan\u00A001,\u00A02020",
                stream: frontend.name,
                stream_id: frontend.stream_id,
                topic: "js",
            },
        ]);
        populate_list_called = true;
    });

    settings_muted_topics.reset();
    assert.equal(settings_muted_topics.loaded, false);

    settings_muted_topics.set_up();
    assert.equal(settings_muted_topics.loaded, true);
    assert.ok(populate_list_called);

    const topic_click_handler = $("body").get_on_handler("click", ".settings-unmute-topic");
    assert.equal(typeof topic_click_handler, "function");

    const event = {
        stopPropagation: noop,
    };

    const topic_fake_this = $.create("fake.settings-unmute-topic");
    const topic_tr_html = $('tr[data-topic="js"]');
    topic_fake_this.closest = (opts) => {
        assert.equal(opts, "tr");
        return topic_tr_html;
    };

    let topic_data_called = 0;
    topic_tr_html.attr = (opts) => {
        if (opts === "data-stream-id") {
            topic_data_called += 1;
            return frontend.stream_id;
        }
        if (opts === "data-topic") {
            topic_data_called += 1;
            return "js";
        }
        throw new Error(`Unknown attribute ${opts}`);
    };

    let unmute_topic_called = false;
    muting_ui.unmute_topic = (stream_id, topic) => {
        assert.equal(stream_id, frontend.stream_id);
        assert.equal(topic, "js");
        unmute_topic_called = true;
    };
    topic_click_handler.call(topic_fake_this, event);
    assert.ok(unmute_topic_called);
    assert.equal(topic_data_called, 2);
});
