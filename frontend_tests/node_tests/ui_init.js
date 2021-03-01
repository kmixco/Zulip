"use strict";

const rewiremock = require("rewiremock/node");

const {stub_templates} = require("../zjsunit/handlebars");
const {set_global, zrequire} = require("../zjsunit/namespace");
const {run_test} = require("../zjsunit/test");
const $ = require("../zjsunit/zjquery");

/*
    This test suite is designed to find errors
    in our initialization sequence.  It doesn't
    really validate any behavior, other than just
    making sure things don't fail.  For more
    directed testing of individual modules, you
    should create dedicated test suites.

    Also, we stub a lot of initialization here that
    is tricky to test due to dependencies on things
    like jQuery.  A good project is to work through
    ignore_modules and try to make this test more
    complete.

    Also, it's good to be alert here for things
    that can be cleaned up in the code--for example,
    not everything needs to happen in `initialization`--
    some things can happen later in a `launch` method.

*/

set_global("document", {
    location: {
        protocol: "http",
    },
});

set_global("csrf_token", "whatever");

const resize = {
    __esModule: true,
    handler: () => {},
};
rewiremock("../../static/js/resize").with(resize);
const page_params = set_global("page_params", {});

page_params.realm_default_streams = [];
page_params.subscriptions = [];
page_params.unsubscribed = [];
page_params.never_subscribed = [];
page_params.realm_notifications_stream_id = -1;
page_params.unread_msgs = {
    huddles: [],
    pms: [],
    streams: [],
    mentions: [],
};
page_params.recent_private_conversations = [];
page_params.user_status = {};
page_params.realm_emoji = {};
page_params.realm_users = [];
page_params.realm_non_active_users = [];
page_params.cross_realm_bots = [];
page_params.muted_topics = [];
page_params.realm_user_groups = [];
page_params.realm_bots = [];
page_params.realm_filters = [];
page_params.starred_messages = [];
page_params.presences = [];

rewiremock("../../static/js/activity").with({initialize() {}});
rewiremock("../../static/js/click_handlers").with({initialize() {}});
rewiremock("../../static/js/compose_pm_pill").with({initialize() {}});
rewiremock("../../static/js/drafts").with({initialize() {}});
rewiremock("../../static/js/emoji_picker").with({initialize() {}});
rewiremock("../../static/js/gear_menu").with({initialize() {}});
rewiremock("../../static/js/hashchange").with({initialize() {}});
rewiremock("../../static/js/hotspots").with({initialize() {}});
// Accesses home_msg_list, which is a lot of complexity to set up
rewiremock("../../static/js/message_fetch").with({initialize() {}});
rewiremock("../../static/js/message_scroll").with({initialize() {}});
const message_viewport = {
    __esModule: true,
    initialize() {},
};
rewiremock("../../static/js/message_viewport").with(message_viewport);
rewiremock("../../static/js/panels").with({initialize() {}});
rewiremock("../../static/js/reload").with({initialize() {}});
rewiremock("../../static/js/scroll_bar").with({initialize() {}});
const server_events = {
    __esModule: true,
    initialize() {},
};
rewiremock("../../static/js/server_events").with(server_events);
rewiremock("../../static/js/settings_sections").with({initialize() {}});
rewiremock("../../static/js/settings_panel_menu").with({initialize() {}});
rewiremock("../../static/js/settings_toggle").with({initialize() {}});
rewiremock("../../static/js/subs").with({initialize() {}});
rewiremock("../../static/js/timerender").with({initialize() {}});
const ui = {
    __esModule: true,
    initialize() {},
};
rewiremock("../../static/js/ui").with(ui);
rewiremock("../../static/js/unread_ui").with({initialize() {}});

server_events.home_view_loaded = () => true;

resize.watch_manual_resize = () => {};

rewiremock("../../static/js/emojisets").with({
    initialize: () => {},
});

rewiremock.enable();

const util = zrequire("util");

const upload = zrequire("upload");
const compose = zrequire("compose");

run_test("initialize_everything", () => {
    util.is_mobile = () => false;
    stub_templates(() => "some-html");
    ui.get_scroll_element = (element) => element;

    const document_stub = $.create("document-stub");
    document.to_$ = () => document_stub;
    document_stub.idle = () => {};

    const window_stub = $.create("window-stub");
    set_global("to_$", () => window_stub);
    window_stub.idle = () => {};
    window_stub.on = () => window_stub;

    message_viewport.message_pane = $(".app");

    const $message_view_header = $.create("#message_view_header");
    $message_view_header.append = () => {};
    upload.__Rewire__("setup_upload", () => {});

    $("#stream_message_recipient_stream").typeahead = () => {};
    $("#stream_message_recipient_topic").typeahead = () => {};
    $("#private_message_recipient").typeahead = () => {};
    $("#compose-textarea").typeahead = () => {};
    $("#search_query").typeahead = () => {};

    const value_stub = $.create("value");
    const count_stub = $.create("count");
    count_stub.set_find_results(".value", value_stub);
    $(".top_left_starred_messages").set_find_results(".count", count_stub);

    $("#message_view_header .stream").length = 0;

    // set find results doesn't work here since we call .empty() in the code.
    $message_view_header.find = () => false;

    compose.__Rewire__("compute_show_video_chat_button", () => {});
    $("#below-compose-content .video_link").toggle = () => {};

    $("<audio>")[0] = "stub";

    zrequire("ui_init");
});

rewiremock.disable();
