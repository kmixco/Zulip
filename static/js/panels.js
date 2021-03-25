import $ from "jquery";

import {localstorage} from "./localstorage";
import * as notifications from "./notifications";
import * as unread_ops from "./unread_ops";
import * as unread_ui from "./unread_ui";
import * as util from "./util";

export function resize_app() {
    const panels_height = $("#panels").height();
    $("body > .app").height("calc(100% - " + panels_height + "px)");

    // the floating recipient bar is usually positioned right below
    // the `.header` element (including padding).
    const frb_top =
        panels_height +
        $(".header").height() +
        Number.parseInt($(".header").css("paddingBottom"), 10);
    $("#floating_recipient_bar").css("top", frb_top + "px");
}

const show_step = function ($process, step) {
    $process
        .find("[data-step]")
        .hide()
        .filter("[data-step=" + step + "]")
        .show();
};

const get_step = function ($process) {
    return $process.find("[data-step]:visible").data("step");
};

function should_show_notifications(ls) {
    // if the user said to never show banner on this computer again, it will
    // be stored as `true` so we want to negate that.
    if (localstorage.supported() && ls.get("dontAskForNotifications") === true) {
        return false;
    }

    return (
        // notifications *basically* don't work on any mobile platforms, so don't
        // event show the banners. This prevents trying to access things that
        // don't exist like `Notification.permission`.
        !util.is_mobile() &&
        // if permission has not been granted yet.
        !notifications.granted_desktop_notifications_permission() &&
        // if permission is allowed to be requested (e.g. not in "denied" state).
        notifications.permission_state() !== "denied"
    );
}

export function check_profile_incomplete() {
    if (!page_params.is_admin) {
        return false;
    }

    // Eventually, we might also check page_params.realm_icon_source,
    // but it feels too aggressive to ask users to do change that
    // since their organization might not have a logo yet.
    if (
        page_params.realm_description === "" ||
        /^Organization imported from [A-Za-z]+[!.]$/.test(page_params.realm_description)
    ) {
        return true;
    }
    return false;
}

export function show_profile_incomplete(is_profile_incomplete) {
    if (is_profile_incomplete) {
        $("[data-process='profile-incomplete']").show();
    } else {
        $("[data-process='profile-incomplete']").hide();
    }
}

export function initialize() {
    const ls = localstorage();
    if (page_params.insecure_desktop_app) {
        open($("[data-process='insecure-desktop-app']"));
    } else if (page_params.warn_no_email === true && page_params.is_admin) {
        // if email has not been set up and the user is the admin,
        // display a warning to tell them to set up an email server.
        open($("[data-process='email-server']"));
    } else if (should_show_notifications(ls)) {
        open($("[data-process='notifications']"));
    } else if (unread_ui.should_display_bankruptcy_banner()) {
        open($("[data-process='bankruptcy']"));
    } else if (check_profile_incomplete()) {
        open($("[data-process='profile-incomplete']"));
    }

    // Configure click handlers.
    $(".request-desktop-notifications").on("click", function (e) {
        e.preventDefault();
        $(this).closest(".alert").hide();
        notifications.request_desktop_notifications_permission();
        resize_app();
    });

    $(".reject-notifications").on("click", function () {
        $(this).closest(".alert").hide();
        ls.set("dontAskForNotifications", true);
        resize_app();
    });

    $(".accept-bankruptcy").on("click", function (e) {
        e.preventDefault();
        $(this).closest(".alert").hide();
        $(".bankruptcy-loader").show();
        setTimeout(unread_ops.mark_all_as_read, 1000);
        resize_app();
    });

    $("#panels").on("click", ".alert .close, .alert .exit", function (e) {
        e.stopPropagation();
        const $process = $(e.target).closest("[data-process]");
        if (get_step($process) === 1 && $process.data("process") === "notifications") {
            show_step($process, 2);
        } else {
            $(this).closest(".alert").hide();
        }
        resize_app();
    });

    // Treat Enter with links in the panels UI focused like a click.,
    $("#panels").on("keyup", ".alert-link[role=button]", function (e) {
        e.stopPropagation();
        if (e.key === "Enter") {
            $(this).click();
        }
    });
}

export function open($process) {
    $("[data-process]").hide();
    $process.show();
    resize_app();
}
