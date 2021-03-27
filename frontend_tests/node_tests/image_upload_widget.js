"use strict";

const {strict: assert} = require("assert");

const {mock_cjs, mock_esm, set_global, zrequire} = require("../zjsunit/namespace");
const {run_test} = require("../zjsunit/test");
const $ = require("../zjsunit/zjquery");

const {ImageUploadWidget} = zrequire("image_upload_widget");

const channel = mock_esm("../../static/js/channel");
mock_esm("../../static/js/csrf", {csrf_token: "csrf_token"});

mock_cjs("jquery", $);

let form_data;

const _FormData = function () {
    return form_data;
};

set_global("FormData", _FormData);

run_test("image_upload_widget", () => {
    function test_complete_upload(spinner, upload_text, delete_button, error_text) {
        assert.equal(error_text.is(":visible"), false);
        assert.equal(spinner.is(":visible"), false);
        assert.equal(upload_text.is(":visible"), true);
        assert.equal(delete_button.is(":visible"), true);
    }

    function test_image_upload(widget) {
        form_data = {
            append(field, val) {
                form_data[field] = val;
            },
        };

        const image_upload_widget = new ImageUploadWidget(null, widget);
        const file_input = [{files: ["image1.png", "image2.png"]}];
        let posted;
        const url = image_upload_widget.url;
        const spinner = $(`#${widget} .upload-spinner-background`);
        const upload_text = $(`#${widget}  .image-upload-text`);
        const delete_button = $(`#${widget}  .image-delete-button`);
        const error_text = $(`#${widget}  .image_file_input_error`);

        channel.post = function (req) {
            posted = true;
            assert.equal(req.data["file-0"], "image1.png");
            assert.equal(req.data["file-1"], "image2.png");
            assert.equal(req.processData, false);
            assert.equal(req.contentType, false);
            assert.equal(req.url, url);
            assert.equal(req.data.csrfmiddlewaretoken, "csrf_token");
            assert.equal(req.cache, false);
            req.success();
            req.error();
        };

        image_upload_widget.image_upload(file_input);
        test_complete_upload(spinner, upload_text, delete_button, error_text);
        assert(posted);
    }

    test_image_upload("realm-icon-upload-widget");
});
