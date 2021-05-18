"use strict";

const {strict: assert} = require("assert");

const {zrequire} = require("../zjsunit/namespace");
const {run_test} = require("../zjsunit/test");
const blueslip = require("../zjsunit/zblueslip");

const {ListCursor} = zrequire("list_cursor");

run_test("config errors", () => {
    blueslip.expect("error", "Programming error");
    new ListCursor({});
});

function basic_conf({first_key, prev_key, next_key}) {
    const list = {
        scroll_container_sel: "whatever",
        find_li: () => {},
        first_key,
        prev_key,
        next_key,
    };

    const conf = {
        list,
        highlight_class: "highlight",
    };

    return conf;
}

run_test("misc errors", (override) => {
    const conf = basic_conf({
        first_key: () => undefined,
        prev_key: () => undefined,
        next_key: () => undefined,
    });

    const cursor = new ListCursor(conf);

    // Test that we just ignore empty
    // lists for unknown keys.
    override(conf.list, "find_li", ({key, force_render}) => {
        assert.equal(key, "nada");
        assert.equal(force_render, true);
        return [];
    });

    cursor.get_row("nada");

    blueslip.expect("error", "Caller is not checking keys for ListCursor.go_to");
    cursor.go_to(undefined);

    blueslip.expect("error", "Cannot highlight key for ListCursor: nada");
    cursor.go_to("nada");

    cursor.prev();
    cursor.next();
});

run_test("single item list", (override) => {
    const valid_key = "42";

    const conf = basic_conf({
        first_key: () => valid_key,
        next_key: () => undefined,
        prev_key: () => undefined,
    });
    const cursor = new ListCursor(conf);

    const li_stub = {
        length: 1,
        addClass: () => {},
    };

    override(conf.list, "find_li", () => li_stub);
    override(cursor, "adjust_scroll", () => {});

    cursor.go_to(valid_key);

    // Test prev/next, which should just silently do nothing.
    cursor.prev();
    cursor.next();

    // The next line is also a noop designed to just give us test
    // coverage.
    cursor.go_to(valid_key);
});
