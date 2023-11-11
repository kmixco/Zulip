import $ from "jquery";

import * as channel from "./channel";
import {page_params} from "./page_params";
import * as presence from "./presence";
import * as recent_view_ui from "./recent_view_ui";
import * as watchdog from "./watchdog";

/*
    Helpers for detecting user activity and managing user idle states
*/

/* Broadcast "idle" to server after 5 minutes of local inactivity */
const DEFAULT_IDLE_TIMEOUT_MS = 5 * 60 * 1000;

/* Keep in sync with views.py:update_active_status_backend() */
export const ACTIVE = "active";

export const IDLE = "idle";

// When you open Zulip in a new browser window, client_is_active
// should be true.  When a server-initiated reload happens, however,
// it should be initialized to false.  We handle this with a check for
// whether the window is focused at initialization time.
export let client_is_active = document.hasFocus && document.hasFocus();

// new_user_input is a more strict version of client_is_active used
// primarily for analytics.  We initialize this to true, to count new
// page loads, but set it to false in the onload function in reload.js
// if this was a server-initiated-reload to avoid counting a
// server-initiated reload as user activity.
export let new_user_input = true;

export function set_new_user_input(value) {
    new_user_input = value;
}

export function clear_for_testing() {
    client_is_active = false;
}

export function mark_client_idle() {
    // When we become idle, we don't immediately send anything to the
    // server; instead, we wait for our next periodic update, since
    // this data is fundamentally not timely.
    client_is_active = false;
}

export function compute_active_status() {
    // The overall algorithm intent for the `status` field is to send
    // `ACTIVE` (aka green circle) if we know the user is at their
    // computer, and IDLE (aka orange circle) if the user might not
    // be:
    //
    // * For the web app, we just know whether this window has focus.
    // * For the electron desktop app, we also know whether the
    //   user is active or idle elsewhere on their system.
    //
    // The check for `get_idle_on_system === undefined` is feature
    // detection; older desktop app releases never set that property.
    if (
        window.electron_bridge !== undefined &&
        window.electron_bridge.get_idle_on_system !== undefined
    ) {
        if (window.electron_bridge.get_idle_on_system()) {
            return IDLE;
        }
        return ACTIVE;
    }

    if (client_is_active) {
        return ACTIVE;
    }
    return IDLE;
}

export function send_presence_to_server(redraw) {
    // Zulip has 2 data feeds coming from the server to the client:
    // The server_events data, and this presence feed.  Data from
    // server_events is nicely serialized, but if we've been offline
    // and not running for a while (e.g. due to suspend), we can end
    // up with inconsistent state where users appear in presence that
    // don't appear in people.js.  We handle this in 2 stages.  First,
    // here, we trigger an extra run of the clock-jump check that
    // detects whether this device just resumed from suspend.  This
    // ensures that watchdog.suspect_offline is always up-to-date
    // before we initiate a presence request.
    //
    // If we did just resume, it will also trigger an immediate
    // server_events request to the server (the success handler to
    // which will clear suspect_offline and potentially trigger a
    // reload if the device was offline for more than
    // DEFAULT_EVENT_QUEUE_TIMEOUT_SECS).
    if (page_params.is_spectator) {
        return;
    }

    watchdog.check_for_unsuspend();

    channel.post({
        url: "/json/users/me/presence",
        data: {
            status: compute_active_status(),
            ping_only: !redraw,
            new_user_input,
            slim_presence: true,
        },
        success(data) {
            // Update Zephyr mirror activity warning
            if (data.zephyr_mirror_active === false) {
                $("#zephyr-mirror-error").addClass("show");
            } else {
                $("#zephyr-mirror-error").removeClass("show");
            }

            new_user_input = false;

            if (redraw) {
                presence.set_info(data.presences, data.server_timestamp);
                redraw();
            }
        },
    });
}

export function mark_client_active() {
    // exported for testing
    if (!client_is_active) {
        client_is_active = true;
        send_presence_to_server();
        recent_view_ui.update_recent_view_rendered_time();
    }
}

export function initialize() {
    $("html").on("mousemove", () => {
        new_user_input = true;
    });

    $(window).on("focus", mark_client_active);
    $(window).idle({
        idle: DEFAULT_IDLE_TIMEOUT_MS,
        onIdle: mark_client_idle,
        onActive: mark_client_active,
        keepTracking: true,
    });
}
