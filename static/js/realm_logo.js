"use strict";

const settings_config = require("./settings_config");

exports.build_realm_logo_widget = function (is_night) {
    let logo_section_id = "#realm-day-logo-upload-widget";
    let logo_source = page_params.realm_logo_source;
    let night_param = false;

    if (is_night) {
        logo_section_id = "#realm-night-logo-upload-widget";
        logo_source = page_params.realm_night_logo_source;
        night_param = true;
    }

    const delete_button_elem = $(logo_section_id + " .image-delete-button");

    if (!page_params.is_admin) {
        return;
    }

    if (logo_source === "D") {
        delete_button_elem.hide();
    } else {
        delete_button_elem.show();
    }

    const data = {night: JSON.stringify(is_night)};
    delete_button_elem.on("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        channel.del({
            url: "/json/realm/logo",
            data,
        });
    });

    return image_upload_widget.build_direct_upload_widget(
        logo_section_id,
        "/json/realm/logo",
        page_params.max_logo_file_size,
        night_param,
    );
};

function change_logo_delete_button(logo_source, logo_delete_button, file_input) {
    if (logo_source === "U") {
        logo_delete_button.show();
    } else {
        logo_delete_button.hide();
        // Need to clear input because of a small edge case
        // where you try to upload the same image you just deleted.
        file_input.val("");
    }
}

exports.rerender = function () {
    const file_input = $("#realm-day-logo-upload-widget .image_file_input");
    const night_file_input = $("#realm-night-logo-upload-widget .realm-logo-file-input");
    $("#realm-day-logo-upload-widget .image-block").attr("src", page_params.realm_logo_url);

    if (page_params.realm_night_logo_source === "D" && page_params.realm_logo_source !== "D") {
        // If no night mode logo is uploaded but a day mode one
        // is, use the day mode one; this handles the common case
        // of transparent background logos that look good on both
        // night and day themes.  See also similar code in admin.js.

        $("#realm-night-logo-upload-widget .image-block").attr("src", page_params.realm_logo_url);
    } else {
        $("#realm-night-logo-upload-widget .image-block").attr(
            "src",
            page_params.realm_night_logo_url,
        );
    }

    if (
        (page_params.color_scheme === settings_config.color_scheme_values.night.code &&
            page_params.realm_night_logo_source !== "D") ||
        (page_params.color_scheme === settings_config.color_scheme_values.automatic.code &&
            page_params.realm_night_logo_source !== "D" &&
            window.matchMedia &&
            window.matchMedia("(prefers-color-scheme: dark)").matches)
    ) {
        $("#realm-logo").attr("src", page_params.realm_night_logo_url);
    } else {
        $("#realm-logo").attr("src", page_params.realm_logo_url);
    }

    change_logo_delete_button(
        page_params.realm_logo_source,
        $("#realm-day-logo-upload-widget .image-delete-button"),
        file_input,
    );
    change_logo_delete_button(
        page_params.realm_night_logo_source,
        $("#realm-night-logo-upload-widget .image-delete-button"),
        night_file_input,
    );
};

window.realm_logo = exports;
