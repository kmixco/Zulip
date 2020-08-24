"use strict";

exports.build_bot_create_widget = function () {
    // We have to do strange gyrations with the file input to clear it,
    // where we replace it wholesale, so we generalize the file input with
    // a callback function.
    const get_file_input = function () {
        return $("#bot_avatar_file_input");
    };

    const file_name_field = $("#bot_avatar_file");
    const input_error = $("#bot_avatar_file_input_error");
    const clear_button = $("#bot_avatar_clear_button");
    const upload_button = $("#bot_avatar_upload_button");

    return upload_widget.build_widget(
        get_file_input,
        file_name_field,
        input_error,
        clear_button,
        upload_button,
    );
};

exports.build_bot_edit_widget = function (target) {
    const get_file_input = function () {
        return target.find(".edit_bot_avatar_file_input");
    };

    const file_name_field = target.find(".edit_bot_avatar_file");
    const input_error = target.find(".edit_bot_avatar_error");
    const clear_button = target.find(".edit_bot_avatar_clear_button");
    const upload_button = target.find(".edit_bot_avatar_upload_button");

    return upload_widget.build_widget(
        get_file_input,
        file_name_field,
        input_error,
        clear_button,
        upload_button,
    );
};

exports.build_user_avatar_widget = function () {
    if (page_params.avatar_source === "G") {
        $("#user-avatar-upload-widget .image-delete-button").hide();
        $("#user-avatar-source").show();
    } else {
        $("#user-avatar-source").hide();
    }

    $("#user-avatar-upload-widget .image-delete-button").on("click keydown", (e) => {
        e.preventDefault();
        e.stopPropagation();
        const file_input = $("#user-avatar-upload-widget .image_file_input").expectOne();
        channel.del({
            url: "/json/users/me/avatar",
            success() {
                $("#user-avatar-upload-widget .image-delete-button").hide();
                $("#user-avatar-source").show();
                // Need to clear input because of a small edge case
                // where you try to upload the same image you just deleted.
                file_input.val("");
                // Rest of the work is done via the user_events -> avatar_url event we will get
            },
        });
    });

    if (settings_account.user_can_change_avatar()) {
        return upload_widget.build_direct_upload_widget(
            "#user-avatar-upload-widget",
            page_params.max_avatar_file_size_mib,
        );
    }
};

window.avatar = exports;
