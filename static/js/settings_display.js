var settings_display = (function () {

var exports = {};

exports.set_night_mode = function (bool) {
    var night_mode = bool;
    var data = { night_mode: JSON.stringify(night_mode) };
    var context = {
        enable_text: data.night_mode === "true" ?
            i18n.t("enabled") :
            i18n.t("disabled"),
    };

    channel.patch({
        url: '/json/settings/display',
        data: data,
        success: function () {
            page_params.night_mode = night_mode;
            if (overlays.settings_open()) {
                ui_report.success(i18n.t("Night mode __enable_text__!", context),
                                  $('#display-settings-status').expectOne());
            }
        },
        error: function (xhr) {
            if (overlays.settings_open()) {
                ui_report.error(i18n.t("Error updating night mode setting."), xhr, $('#display-settings-status').expectOne());
            }
        },
    });
};

exports.set_up = function () {
    $("#display-settings-status").hide();

    $("#user_timezone").val(page_params.timezone);
    $(".emojiset_choice[value=" + page_params.emojiset + "]").prop("checked", true);

    $("#default_language_modal [data-dismiss]").click(function () {
        overlays.close_modal('default_language_modal');
    });

    $("#default_language_modal .language").click(function (e) {
        e.preventDefault();
        e.stopPropagation();
        overlays.close_modal('default_language_modal');

        var data = {};
        var $link = $(e.target).closest("a[data-code]");
        var setting_value = $link.attr('data-code');
        data.default_language = JSON.stringify(setting_value);

        var new_language = $link.attr('data-name');
        $('#default_language_name').text(new_language);

        var context = {};
        context.lang = new_language;

        channel.patch({
            url: '/json/settings/display',
            data: data,
            success: function () {
                ui_report.success(i18n.t("__lang__ is now the default language!  You will need to reload the window for your changes to take effect", context),
                                  $('#display-settings-status').expectOne());
            },
            error: function (xhr) {
                ui_report.error(i18n.t("Error updating default language setting"), xhr, $('#display-settings-status').expectOne());
            },
        });
    });

    $('#default_language').on('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        overlays.open_modal('default_language_modal');
    });

    $("#high_contrast_mode").change(function () {
        var high_contrast_mode = this.checked;
        var data = {};
        data.high_contrast_mode = JSON.stringify(high_contrast_mode);
        var context = {};
        if (data.high_contrast_mode === "true") {
            context.enabled_or_disabled = i18n.t('Enabled');
        } else {
            context.enabled_or_disabled = i18n.t('Disabled');
        }

        channel.patch({
            url: '/json/settings/display',
            data: data,
            success: function () {
                ui_report.success(i18n.t("High contrast mode __enabled_or_disabled__!", context),
                                  $('#display-settings-status').expectOne());
            },
            error: function (xhr) {
                ui_report.error(i18n.t("Error updating high contrast setting"), xhr, $('#display-settings-status').expectOne());
            },
        });
    });

    $("#night_mode").change(function () {
        exports.set_night_mode(this.checked);
    });

    $("#left_side_userlist").change(function () {
        var left_side_userlist = this.checked;
        var data = {};
        data.left_side_userlist = JSON.stringify(left_side_userlist);
        var context = {};
        if (data.left_side_userlist === "true") {
            context.side = i18n.t('left');
        } else {
            context.side = i18n.t('right');
        }

        channel.patch({
            url: '/json/settings/display',
            data: data,
            success: function () {
                ui_report.success(i18n.t("User list will appear on the __side__ hand side! You will need to reload the window for your changes to take effect.", context),
                                  $('#display-settings-status').expectOne());
            },
            error: function (xhr) {
                ui_report.error(i18n.t("Error updating user list placement setting"), xhr, $('#display-settings-status').expectOne());
            },
        });
    });

    $("#twenty_four_hour_time").change(function () {
        var data = {};
        var setting_value = $("#twenty_four_hour_time").is(":checked");
        data.twenty_four_hour_time = JSON.stringify(setting_value);
        var context = {};
        if (data.twenty_four_hour_time === "true") {
            context.format = '24';
        } else {
            context.format = '12';
        }

        channel.patch({
            url: '/json/settings/display',
            data: data,
            success: function () {
                ui_report.success(i18n.t("Time will now be displayed in the __format__-hour format!", context),
                                  $('#display-settings-status').expectOne());
            },
            error: function (xhr) {
                ui_report.error(i18n.t("Error updating time format setting"), xhr, $('#display-settings-status').expectOne());
            },
        });
    });

    $("#user_timezone").change(function () {
        var data = {};
        var timezone = this.value;
        data.timezone = JSON.stringify(timezone);

        channel.patch({
            url: '/json/settings/display',
            data: data,
            success: function () {
                ui_report.success(i18n.t("Your time zone have been set to __timezone__", {timezone: timezone}), $('#display-settings-status').expectOne());
            },
            error: function (xhr) {
                ui_report.error(i18n.t("Error updating time zone"), xhr, $('#display-settings-status').expectOne());
            },
        });
    });

    $(".emojiset_choice").click(function () {
        var emojiset = $(this).val();
        var data = {};
        data.emojiset = JSON.stringify(emojiset);

        channel.patch({
            url: '/json/settings/display',
            data: data,
            success: function () {
                var spinner = $("#emojiset_spinner").expectOne();
                loading.make_indicator(spinner, {text: 'Changing emojiset.'});
            },
            error: function (xhr) {
                ui_report.error(i18n.t("Error changing emojiset."), xhr, $('#display-settings-status').expectOne());
            },
        });
    });
};

exports.report_emojiset_change = function () {
    function emoji_success() {
        if ($("#display-settings-status").length) {
            loading.destroy_indicator($("#emojiset_spinner"));
            $("#emojiset_select").val(page_params.emojiset);
            ui_report.success(i18n.t("Emojiset changed successfully!"),
                              $('#display-settings-status').expectOne());
        }
    }

    if (page_params.emojiset === 'text') {
        emoji_success();
        return;
    }

    var sprite = new Image();
    sprite.onload = function () {
        var sprite_css_href = "/static/generated/emoji/" + page_params.emojiset + "_sprite.css";
        $("#emoji-spritesheet").attr('href', sprite_css_href);
        emoji_success();
    };
    sprite.src = "/static/generated/emoji/sheet_" + page_params.emojiset + "_32.png";
};

function _update_page() {
    $("#twenty_four_hour_time").prop('checked', page_params.twenty_four_hour_time);
    $("#left_side_userlist").prop('checked', page_params.left_side_userlist);
    $("#default_language_name").text(page_params.default_language_name);
}

exports.update_page = function () {
    i18n.ensure_i18n(_update_page);
};

return exports;
}());

if (typeof module !== 'undefined') {
    module.exports = settings_display;
}
