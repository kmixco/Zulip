"use strict";

const {strict: assert} = require("assert");

const _ = require("lodash");

const {i18n} = require("../zjsunit/i18n");
const {mock_cjs, zrequire} = require("../zjsunit/namespace");
const {run_test} = require("../zjsunit/test");

let env;

function make_tab(i) {
    const self = {};

    assert.equal(env.tabs.length, i);

    self.stub = true;
    self.class = [];

    self.addClass = (c) => {
        self.class += " " + c;
        const tokens = self.class.trim().split(/ +/);
        self.class = _.uniq(tokens).join(" ");
    };

    self.removeClass = (c) => {
        const tokens = self.class.trim().split(/ +/);
        self.class = _.without(tokens, c).join(" ");
    };

    self.hasClass = (c) => {
        const tokens = self.class.trim().split(/ +/);
        return tokens.includes(c);
    };

    self.data = (name) => {
        assert.equal(name, "tab-id");
        return i;
    };

    self.text = (text) => {
        assert.equal(
            text,
            [
                "translated: Keyboard shortcuts",
                "translated: Message formatting",
                "translated: Search operators",
            ][i],
        );
    };

    self.trigger = (type) => {
        if (type === "focus") {
            env.focused_tab = i;
        }
    };

    env.tabs.push(self);

    return self;
}

const ind_tab = (function () {
    const self = {};

    self.stub = true;

    self.on = (name, f) => {
        if (name === "click") {
            env.click_f = f;
        } else if (name === "keydown") {
            env.keydown_f = f;
        }
    };

    self.removeClass = (c) => {
        for (const tab of env.tabs) {
            tab.removeClass(c);
        }
    };

    self.eq = (idx) => env.tabs[idx];

    return self;
})();

function make_switcher() {
    const self = {};

    self.stub = true;

    self.children = [];

    self.classList = new Set();

    self.append = (child) => {
        self.children.push(child);
    };

    self.addClass = (c) => {
        self.classList.add(c);
        self.addedClass = c;
    };

    self.find = (sel) => {
        switch (sel) {
            case ".ind-tab":
                return ind_tab;
            default:
                throw new Error("unknown selector: " + sel);
        }
    };

    return self;
}

mock_cjs("jquery", (sel, attributes) => {
    if (sel.stub) {
        // The component often redundantly re-wraps objects.
        return sel;
    }

    switch (sel) {
        case "<div class='tab-switcher'></div>":
            return env.switcher;
        case "<div class='tab-switcher stream_sorter_toggle'></div>":
            return env.switcher;
        case "<div>": {
            const tab_id = attributes["data-tab-id"];
            assert.deepEqual(
                attributes,
                [
                    {
                        class: "ind-tab",
                        "data-tab-key": "keyboard-shortcuts",
                        "data-tab-id": 0,
                        tabindex: 0,
                    },
                    {
                        class: "ind-tab",
                        "data-tab-key": "message-formatting",
                        "data-tab-id": 1,
                        tabindex: 0,
                    },
                    {
                        class: "ind-tab",
                        "data-tab-key": "search-operators",
                        "data-tab-id": 2,
                        tabindex: 0,
                    },
                ][tab_id],
            );
            return make_tab(tab_id);
        }
        default:
            throw new Error("unknown selector: " + sel);
    }
});

const components = zrequire("components");

const noop = () => {};

const LEFT_KEY = {which: 37, preventDefault: noop, stopPropagation: noop};
const RIGHT_KEY = {which: 39, preventDefault: noop, stopPropagation: noop};

run_test("basics", () => {
    env = {
        keydown_f: undefined,
        click_f: undefined,
        tabs: [],
        focused_tab: undefined,
        switcher: make_switcher(),
    };

    let callback_args;
    let callback_value;

    let widget = null;
    widget = components.toggle({
        selected: 0,
        values: [
            {label: i18n.t("Keyboard shortcuts"), key: "keyboard-shortcuts"},
            {label: i18n.t("Message formatting"), key: "message-formatting"},
            {label: i18n.t("Search operators"), key: "search-operators"},
        ],
        html_class: "stream_sorter_toggle",
        callback(name, key) {
            assert.equal(callback_args, undefined);
            callback_args = [name, key];

            // The subs code tries to get a widget value in the middle of a
            // callback, which can lead to obscure bugs.
            if (widget) {
                callback_value = widget.value();
            }
        },
    });

    assert.equal(widget.get(), env.switcher);

    assert.deepEqual(env.switcher.children, env.tabs);

    assert.equal(env.switcher.addedClass, "stream_sorter_toggle");

    assert.equal(env.focused_tab, 0);
    assert.equal(env.tabs[0].class, "first selected");
    assert.equal(env.tabs[1].class, "middle");
    assert.equal(env.tabs[2].class, "last");
    assert.deepEqual(callback_args, ["translated: Keyboard shortcuts", "keyboard-shortcuts"]);
    assert.equal(widget.value(), "translated: Keyboard shortcuts");

    callback_args = undefined;

    widget.goto("message-formatting");
    assert.equal(env.focused_tab, 1);
    assert.equal(env.tabs[0].class, "first");
    assert.equal(env.tabs[1].class, "middle selected");
    assert.equal(env.tabs[2].class, "last");
    assert.deepEqual(callback_args, ["translated: Message formatting", "message-formatting"]);
    assert.equal(widget.value(), "translated: Message formatting");

    // Go to same tab twice and make sure we get callback.
    callback_args = undefined;
    widget.goto("message-formatting");
    assert.deepEqual(callback_args, ["translated: Message formatting", "message-formatting"]);

    callback_args = undefined;
    env.keydown_f.call(env.tabs[env.focused_tab], RIGHT_KEY);
    assert.equal(env.focused_tab, 2);
    assert.equal(env.tabs[0].class, "first");
    assert.equal(env.tabs[1].class, "middle");
    assert.equal(env.tabs[2].class, "last selected");
    assert.deepEqual(callback_args, ["translated: Search operators", "search-operators"]);
    assert.equal(widget.value(), "translated: Search operators");
    assert.equal(widget.value(), callback_value);

    // try to crash the key handler
    env.keydown_f.call(env.tabs[env.focused_tab], RIGHT_KEY);
    assert.equal(widget.value(), "translated: Search operators");

    callback_args = undefined;

    env.keydown_f.call(env.tabs[env.focused_tab], LEFT_KEY);
    assert.equal(widget.value(), "translated: Message formatting");

    callback_args = undefined;

    env.keydown_f.call(env.tabs[env.focused_tab], LEFT_KEY);
    assert.equal(widget.value(), "translated: Keyboard shortcuts");

    // try to crash the key handler
    env.keydown_f.call(env.tabs[env.focused_tab], LEFT_KEY);
    assert.equal(widget.value(), "translated: Keyboard shortcuts");

    callback_args = undefined;
    widget.disable_tab("message-formatting");

    env.keydown_f.call(env.tabs[env.focused_tab], RIGHT_KEY);
    assert.equal(widget.value(), "translated: Search operators");

    callback_args = undefined;

    env.keydown_f.call(env.tabs[env.focused_tab], LEFT_KEY);
    assert.equal(widget.value(), "translated: Keyboard shortcuts");

    widget.enable_tab("message-formatting");

    callback_args = undefined;

    env.click_f.call(env.tabs[1]);
    assert.equal(widget.value(), "translated: Message formatting");

    callback_args = undefined;
    widget.disable_tab("search-operators");
    assert.equal(env.tabs[2].hasClass("disabled"), true);
    assert.equal(env.tabs[2].class, "last disabled");

    widget.goto("keyboard-shortcuts");
    assert.equal(env.focused_tab, 0);
    widget.goto("search-operators");
    assert.equal(env.focused_tab, 0);
});
