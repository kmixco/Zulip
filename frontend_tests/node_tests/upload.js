set_global('$', global.make_zjquery());
set_global('document', {
    location: { },
});
set_global('navigator', {
    userAgent: 'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)',
});
set_global('i18n', global.stub_i18n);
set_global('page_params', {
    max_file_upload_size: 25,
});
set_global('csrf_token', { });
global.patch_builtin('window', {
    bridge: false,
});

// Setting these up so that we can test that links to uploads within messages are
// automatically converted to server relative links.
global.document.location.protocol = 'https:';
global.document.location.host = 'foo.com';

zrequire('compose_ui');
zrequire('compose_state');
zrequire('compose');
zrequire('upload');

const upload_opts = upload.options({ mode: "compose" });

run_test('upload_started', () => {
    $("#compose-send-button").prop('disabled', false);
    $("#compose-send-status").removeClass("alert-info").hide();
    $(".compose-send-status-close").one = function (ev_name, handler) {
        assert.equal(ev_name, 'click');
        assert(handler);
    };
    $("#compose-error-msg").html('');
    const test_html = '<div class="progress active">' +
                    '<div class="bar" id="compose-upload-bar-1549958107000" style="width: 0"></div>' +
                    '</div>';
    $("#compose-send-status").append = function (html) {
        assert.equal(html, test_html);
    };
    $('#compose-textarea').caret = function () {
        return 0;
    };
    document.execCommand = function (command, show_default, value) {
        assert.equal(value, "[Uploading some-file…]() ");
    };

    upload_opts.drop();
    upload_opts.uploadStarted(0, {
        trackingId: "1549958107000",
        name: 'some-file',
    }, 1);

    assert.equal($("#compose-send-button").attr("disabled"), '');
    assert($("#compose-send-status").hasClass("alert-info"));
    assert($("#compose-send-status").visible());
    assert.equal($("<p>").text(), 'translated: Uploading…');
});

run_test('progress_updated', () => {
    let width_update_checked = false;
    $("#compose-upload-bar-1549958107000").width = function (width_percent) {
        assert.equal(width_percent, '39%');
        width_update_checked = true;
    };
    upload_opts.progressUpdated(1, {trackingId: "1549958107000"}, 39);
    assert(width_update_checked);
});

run_test('upload_error', () => {
    function setup_test() {
        $("#compose-send-status").removeClass("alert-error");
        $("#compose-send-status").addClass("alert-info");
        $("#compose-send-button").attr("disabled", 'disabled');
        $("#compose-error-msg").text('');

        $("#compose-upload-bar-1549958107000").parent = function () {
            return { remove: function () {} };
        };
    }

    function assert_side_effects(msg) {
        assert($("#compose-send-status").hasClass("alert-error"));
        assert(!$("#compose-send-status").hasClass("alert-info"));
        assert.equal($("#compose-send-button").prop("disabled"), false);
        assert.equal($("#compose-error-msg").text(), msg);
    }

    function test(err, msg, server_response = null, file = {}) {
        setup_test();
        file.trackingId = "1549958107000";
        upload_opts.error(err, server_response, file);
        assert_side_effects(msg);
    }

    const msg_prefix = 'translated: ';
    const msg_1 = 'File upload is not yet available for your browser.';
    const msg_2 = 'Unable to upload that many files at once.';
    const msg_3 = '"foobar.txt" was too large; the maximum file size is 25MB.';
    const msg_4 = 'Sorry, the file was too large.';
    const msg_5 = 'An unknown error occurred.';
    const msg_6 = 'File and image uploads have been disabled for this organization.';

    test('BrowserNotSupported', msg_prefix + msg_1);
    test('TooManyFiles', msg_prefix + msg_2);
    test('FileTooLarge', msg_prefix + msg_3, null, {name: 'foobar.txt'});
    test(413, msg_prefix + msg_4);
    test(400, 'ちょっと…', {msg: 'ちょっと…'});
    test('Do-not-match-any-case', msg_prefix + msg_5);

    // If uploading files has been disabled, then a different error message is
    // displayed when a user tries to paste or drag a file onto the UI.
    page_params.max_file_upload_size = 0;
    test('FileTooLarge', msg_prefix + msg_6, null);
});

run_test('upload_finish', () => {
    function test(i, response, textbox_val) {
        let compose_ui_autosize_textarea_checked = false;
        let compose_actions_start_checked = false;
        let syntax_to_replace;
        let syntax_to_replace_with;
        let file_input_clear = false;

        function setup() {
            $("#compose-textarea").val('');
            compose_ui.autosize_textarea = function () {
                compose_ui_autosize_textarea_checked = true;
            };
            compose_ui.replace_syntax = function (old_syntax, new_syntax) {
                syntax_to_replace = old_syntax;
                syntax_to_replace_with = new_syntax;
            };
            compose_state.set_message_type();
            global.compose_actions = {
                start: function (msg_type) {
                    assert.equal(msg_type, 'stream');
                    compose_actions_start_checked = true;
                },
            };
            $("#compose-send-button").attr('disabled', 'disabled');
            $("#compose-send-status").addClass("alert-info");
            $("#compose-send-status").show();

            $('#file_input').clone = function (param) {
                assert(param);
                return $('#file_input');
            };

            $('#file_input').replaceWith = function (elem) {
                assert.equal(elem, $('#file_input'));
                file_input_clear = true;
            };

            $("#compose-upload-bar-1549958107000").parent = function () {
                return { remove: function () {$('div.progress.active').length = 0;} };
            };
        }

        function assert_side_effects() {
            if (response.uri) {
                assert.equal(syntax_to_replace, '[Uploading some-file…]()');
                assert.equal(syntax_to_replace_with, textbox_val);
                assert(compose_actions_start_checked);
                assert(compose_ui_autosize_textarea_checked);
                assert.equal($("#compose-send-button").prop('disabled'), false);
                assert(!$('#compose-send-status').hasClass('alert-info'));
                assert(!$('#compose-send-status').visible());
                assert(file_input_clear);
            }
        }

        global.patch_builtin('setTimeout', function (func) {
            func();
        });

        $("#compose-upload-bar-1549958107000").width = function (width_percent) {
            assert.equal(width_percent, '100%');
        };

        setup();
        upload_opts.uploadFinished(i, {
            trackingId: "1549958107000",
            name: 'some-file',
        }, response);
        upload_opts.progressUpdated(1, {trackingId: "1549958107000"}, 100);
        assert_side_effects();
    }

    const msg_1 = '[pasted image](https://foo.com/uploads/122456)';
    const msg_2 = '[foobar.jpeg](https://foo.com/user_uploads/foobar.jpeg)';

    test(-1, {}, '');
    test(-1, {uri: 'https://foo.com/uploads/122456'}, msg_1);
    test(1, {uri: '/user_uploads/foobar.jpeg'}, msg_2);
});
