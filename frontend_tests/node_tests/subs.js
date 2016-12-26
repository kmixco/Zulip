global.stub_out_jquery();

add_dependencies({
    stream_data: 'js/stream_data',
    Handlebars: 'handlebars',
    templates: 'js/templates',
    i18n: 'i18next',
});

var subs = require('js/subs.js');

var jsdom = require("jsdom");
var window = jsdom.jsdom().defaultView;
global.$ = require('jquery')(window);

var i18n = global.i18n;
i18n.init({
    nsSeparator: false,
    keySeparator: false,
    interpolation: {
        prefix: "__",
        suffix: "__",
    },
    lng: 'en',
});


(function test_filter_table() {
    var denmark = {
        subscribed: false,
        name: 'Denmark',
        stream_id: 1,
    };
    var poland = {
        subscribed: true,
        name: 'Poland',
        stream_id: 2
    };
    var pomona = {
        subscribed: true,
        name: 'Pomona',
        stream_id: 3
    };

    var elem_1 = $(global.render_template("subscription", denmark));
    var elem_2 = $(global.render_template("subscription", poland));
    var elem_3 = $(global.render_template("subscription", pomona));

    $("body").empty();
    $("body").append('<div id="subscriptions_table"></div>');
    var streams_list = $('<div class="streams-list"></div>');
    $("#subscriptions_table").append(streams_list);

    stream_data.add_sub("Denmark", denmark);
    stream_data.add_sub("Poland", poland);
    stream_data.add_sub("Pomona", pomona);

    streams_list.append(elem_1);
    streams_list.append(elem_2);
    streams_list.append(elem_3);

    // Search with single keyword
    subs.filter_table({input: "Po", subscribed_only: false});
    assert(elem_1.hasClass("notdisplayed"));
    assert(!elem_2.hasClass("notdisplayed"));
    assert(!elem_3.hasClass("notdisplayed"));

    // Search with multiple keywords
    subs.filter_table({input: "Denmark, Pol", subscribed_only: false});
    assert(!elem_1.hasClass("notdisplayed"));
    assert(!elem_2.hasClass("notdisplayed"));
    assert(elem_3.hasClass("notdisplayed"));

    subs.filter_table({input: "Den, Pol", subscribed_only: false});
    assert(elem_1.hasClass("notdisplayed"));
    assert(!elem_2.hasClass("notdisplayed"));
    assert(elem_3.hasClass("notdisplayed"));

    // Search is case-insensitive
    subs.filter_table({input: "po", subscribed_only: false});
    assert(elem_1.hasClass("notdisplayed"));
    assert(!elem_2.hasClass("notdisplayed"));
    assert(!elem_3.hasClass("notdisplayed"));

    // Search subscribed streams only
    subs.filter_table({input: "d", subscribed_only: true});
    assert(elem_1.hasClass("notdisplayed"));
    assert(!elem_2.hasClass("notdisplayed"));
    assert(elem_3.hasClass("notdisplayed"));

    // data-temp-view condition
    elem_1.attr("data-temp-view", "true");

    subs.filter_table({input: "d", subscribed_only: true});
    assert(!elem_1.hasClass("notdisplayed"));
    assert(!elem_2.hasClass("notdisplayed"));
    assert(elem_3.hasClass("notdisplayed"));

    elem_1.attr("data-temp-view", "false");

    subs.filter_table({input: "d", subscribed_only: true});
    assert(elem_1.hasClass("notdisplayed"));
    assert(!elem_2.hasClass("notdisplayed"));
    assert(elem_3.hasClass("notdisplayed"));

    elem_1.removeAttr("data-temp-view");

    // active stream-row is not included in results
    elem_1.addClass("active");
    $("#subscriptions_table").append($('<div class="right"></div>'));
    $(".right").append($('<div class="settings"></div>'));
    $(".right").append($('<div class="nothing-selected"></div>').hide());

    subs.filter_table({input: "d", subscribed_only: true});
    assert(!elem_1.hasClass("active"));
    assert.equal($(".right .settings").css("display"), "none");
    assert.notEqual($(".right .nothing-selected").css("display"), "none");
}());

