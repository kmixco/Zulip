import $ from "jquery";
import assert from "minimalistic-assert";

import render_stream_info_popover from "../templates/popovers/stream_info_popover.hbs";

import * as browser_history from "./browser_history";
import * as hash_util from "./hash_util";
import * as modals from "./modals";
import * as popover_menus from "./popover_menus";
import {current_user} from "./state_data";
import * as stream_data from "./stream_data";
import * as sub_store from "./sub_store";
import * as ui_util from "./ui_util";

let stream_id: number | undefined;

export function initialize(): void {
    popover_menus.register_popover_menu(".pill[data-stream-id]", {
        theme: "popover-menu",
        placement: "right",
        onShow(instance) {
            popover_menus.popover_instances.stream_info_popover = instance;
            popover_menus.on_show_prep(instance);

            const $elt = $(instance.reference);
            const stream_id_str = $elt.attr("data-stream-id");
            assert(stream_id_str !== undefined);
            stream_id = Number.parseInt(stream_id_str, 10);

            instance.setContent(
                ui_util.parse_html(
                    render_stream_info_popover({
                        stream: {
                            ...sub_store.get(stream_id),
                        },
                    }),
                ),
            );
        },
        onMount(instance) {
            const $popper = $(instance.popper);

            // Stream settings
            $popper.on("click", ".open_stream_settings", () => {
                assert(stream_id !== undefined);
                const sub = sub_store.get(stream_id);
                assert(sub !== undefined);
                popover_menus.hide_current_popover_if_visible(instance);
                // modals.close_active_if_any() is mainly used to handle navigation to channel settings
                // using the popover that is opened when clicking on channel pills in the invite user modal.
                modals.close_active_if_any();
                const can_change_name_description = current_user.is_admin;
                const can_change_stream_permissions = stream_data.can_change_permissions(sub);
                let stream_edit_hash = hash_util.channels_settings_edit_url(sub, "general");
                if (!can_change_stream_permissions && !can_change_name_description) {
                    stream_edit_hash = hash_util.channels_settings_edit_url(sub, "personal");
                }
                browser_history.go_to_location(stream_edit_hash);
            });
        },
        onHidden(instance) {
            instance.destroy();
            popover_menus.popover_instances.stream_info_popover = null;
        },
    });
}
