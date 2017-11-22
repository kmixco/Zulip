zrequire('compose_ui');

function make_textbox(s) {
    // Simulate a jQuery textbox for testing purposes.
    var widget = {};

    widget.s = s;
    widget.focused = false;

    widget.caret = function (arg) {
        if (typeof arg === 'number') {
            widget.pos = arg;
            return;
        }

        if (arg) {
            widget.insert_pos = widget.pos;
            widget.insert_text = arg;
            var before = widget.s.slice(0, widget.pos);
            var after = widget.s.slice(widget.pos);
            widget.s = before + arg + after;
            widget.pos += arg.length;
            return;
        }

        return widget.pos;
    };

    widget.focus = function () {
        widget.focused = true;
    };

    widget.blur = function () {
        widget.focused = false;
    };

    widget.val = function () {
        return widget.s;
    };

    widget.trigger = function () {
        return;
    };

    return widget;
}

(function test_smart_insert() {
    var textbox = make_textbox('abc ');
    textbox.caret(4);

    compose_ui.smart_insert(textbox, ':smile:');
    assert.equal(textbox.insert_pos, 4);
    assert.equal(textbox.insert_text, ':smile:');
    assert.equal(textbox.val(), 'abc :smile:');
    assert(textbox.focused);

    textbox.blur();
    compose_ui.smart_insert(textbox, ':airplane:');
    assert.equal(textbox.insert_text, ' :airplane:');
    assert.equal(textbox.val(), 'abc :smile: :airplane:');
    assert(textbox.focused);

    textbox.caret(0);
    textbox.blur();
    compose_ui.smart_insert(textbox, ':octopus:');
    assert.equal(textbox.insert_text, ':octopus: ');
    assert.equal(textbox.val(), ':octopus: abc :smile: :airplane:');
    assert(textbox.focused);

    textbox.caret(textbox.val().length);
    textbox.blur();
    compose_ui.smart_insert(textbox, ':heart:');
    assert.equal(textbox.insert_text, ' :heart:');
    assert.equal(textbox.val(), ':octopus: abc :smile: :airplane: :heart:');
    assert(textbox.focused);

    // Note that we don't have any special logic for strings that are
    // already surrounded by spaces, since we are usually inserting things
    // like emojis and file links.
}());

