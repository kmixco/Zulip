"use strict";

exports.build_realm_icon_widget = function () {
    if (!page_params.is_admin) {
        return;
    }
    if (page_params.realm_icon_source === "G") {
        $("#realm-icon-upload-widget .image-delete-button").hide();
    } else {
        $("#realm-icon-upload-widget .image-delete-button").show();
    }
    $("#realm-icon-upload-widget .image-delete-button").on("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        channel.del({
            url: "/json/realm/icon",
        });
    });

    return image_upload_widget.build_direct_upload_widget(
        "#realm-icon-upload-widget",
        "/json/realm/icon",
        page_params.max_icon_file_size,
    );
};

exports.rerender = function () {
    $("#realm-icon-upload-widget .image-block").attr("src", page_params.realm_icon_url);
    if (page_params.realm_icon_source === "U") {
        $("#realm-icon-upload-widget .image-delete-button").show();
    } else {
        $("#realm-icon-upload-widget .image-delete-button").hide();
        // Need to clear input because of a small edge case
        // where you try to upload the same image you just deleted.
        const file_input = $("#realm-icon-upload-widget .image_file_input");
        file_input.val("");
    }
};

window.realm_icon = exports;
