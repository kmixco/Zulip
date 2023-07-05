/* Module for popovers that have been ported to the modern
   TippyJS/Popper popover library from the legacy Bootstrap
   popovers system in popovers.js. */

import ClipboardJS from "clipboard";
import $ from "jquery";
import tippy, {delegate} from "tippy.js";

import render_actions_popover_content from "../templates/actions_popover_content.hbs";
import render_all_messages_sidebar_actions from "../templates/all_messages_sidebar_actions.hbs";
import render_compose_control_buttons_popover from "../templates/compose_control_buttons_popover.hbs";
import render_compose_select_enter_behaviour_popover from "../templates/compose_select_enter_behaviour_popover.hbs";
import render_delete_topic_modal from "../templates/confirm_dialog/confirm_delete_topic.hbs";
import render_drafts_sidebar_actions from "../templates/drafts_sidebar_action.hbs";
import render_left_sidebar_stream_setting_popover from "../templates/left_sidebar_stream_setting_popover.hbs";
import render_mobile_message_buttons_popover_content from "../templates/mobile_message_buttons_popover_content.hbs";
import render_send_later_modal from "../templates/send_later_modal.hbs";
import render_send_later_popover from "../templates/send_later_popover.hbs";
import render_starred_messages_sidebar_actions from "../templates/starred_messages_sidebar_actions.hbs";
import render_topic_sidebar_actions from "../templates/topic_sidebar_actions.hbs";
import render_user_info_popover_content from "../templates/user_info_popover_content.hbs";

import * as blueslip from "./blueslip";
import * as channel from "./channel";
import * as common from "./common";
import * as compose from "./compose";
import * as compose_actions from "./compose_actions";
import * as compose_state from "./compose_state";
import * as compose_ui from "./compose_ui";
import * as compose_validate from "./compose_validate";
import * as condense from "./condense";
import * as confirm_dialog from "./confirm_dialog";
import * as dialog_widget from "./dialog_widget";
import * as drafts from "./drafts";
import * as emoji_picker from "./emoji_picker";
import * as flatpickr from "./flatpickr";
import * as giphy from "./giphy";
import {$t, $t_html} from "./i18n";
import * as message_edit from "./message_edit";
import * as message_edit_history from "./message_edit_history";
import * as message_lists from "./message_lists";
import * as message_viewport from "./message_viewport";
import * as muted_users_ui from "./muted_users_ui";
import * as narrow from "./narrow";
import * as narrow_state from "./narrow_state";
import * as overlays from "./overlays";
import * as people from "./people";
import * as popover_menus_data from "./popover_menus_data";
import * as popovers from "./popovers";
import * as read_receipts from "./read_receipts";
import * as rows from "./rows";
import * as scheduled_messages from "./scheduled_messages";
import * as settings_bots from "./settings_bots";
import * as settings_data from "./settings_data";
import * as settings_users from "./settings_users";
import * as starred_messages from "./starred_messages";
import * as starred_messages_ui from "./starred_messages_ui";
import * as stream_popover from "./stream_popover";
import * as timerender from "./timerender";
import * as ui_report from "./ui_report";
import {parse_html} from "./ui_util";
import * as unread_ops from "./unread_ops";
import * as user_profile from "./user_profile";
import {user_settings} from "./user_settings";
import * as user_status from "./user_status";
import * as user_topics from "./user_topics";

let message_actions_popover_keyboard_toggle = false;
let selected_send_later_timestamp;
let user_card_popover_from_hotkey;

const popover_instances = {
    compose_control_buttons: null,
    starred_messages: null,
    drafts: null,
    all_messages: null,
    message_actions: null,
    stream_settings: null,
    compose_mobile_button: null,
    compose_enter_sends: null,
    topics_menu: null,
    send_later: null,
    user_card: null,
};

export function sidebar_menu_instance_handle_keyboard(instance, key) {
    const items = get_popover_items_for_instance(instance);
    popovers.popover_items_handle_keyboard(key, items);
}

export function get_visible_instance() {
    return Object.values(popover_instances).find(Boolean);
}

export function get_current_user_card_instance() {
    return popover_instances.user_card;
}

export function get_topic_menu_popover() {
    return popover_instances.topics_menu;
}

export function get_selected_send_later_timestamp() {
    if (!selected_send_later_timestamp) {
        return undefined;
    }
    return selected_send_later_timestamp;
}

export function get_formatted_selected_send_later_time() {
    const current_time = Date.now() / 1000; // seconds, like selected_send_later_timestamp
    if (
        scheduled_messages.is_send_later_timestamp_missing_or_expired(
            selected_send_later_timestamp,
            current_time,
        )
    ) {
        return undefined;
    }
    return timerender.get_full_datetime(new Date(selected_send_later_timestamp * 1000), "time");
}

export function set_selected_schedule_timestamp(timestamp) {
    selected_send_later_timestamp = timestamp;
}

export function reset_selected_schedule_timestamp() {
    selected_send_later_timestamp = undefined;
}

export function get_scheduled_messages_popover() {
    return popover_instances.send_later;
}

export function get_compose_control_buttons_popover() {
    return popover_instances.compose_control_buttons;
}

export function get_starred_messages_popover() {
    return popover_instances.starred_messages;
}

export function is_compose_enter_sends_popover_displayed() {
    return popover_instances.compose_enter_sends?.state.isVisible;
}

function get_popover_items_for_instance(instance) {
    const $current_elem = $(instance.popper);
    const class_name = $current_elem.attr("class");

    if (!$current_elem) {
        blueslip.error("Trying to get menu items when popover is closed.", {class_name});
        return undefined;
    }

    return $current_elem.find("li:not(.divider):visible a");
}

export function show_sender_info() {
    const $message = $(".selected_message");
    if ($message[0]._tippy) {
        $message[0]._tippy.destroy();
    } else {
        user_card_popover_from_hotkey().show();
    }

    const interval = setInterval(() => {
        if (get_current_user_card_instance()) {
            clearInterval(interval);
            const $items = get_popover_items_for_instance(get_current_user_card_instance());

            popovers.focus_first_popover_item($items);
        }
    }, 50);
}

export function user_info_popover_handle_keyboard(key) {
    const $items = get_popover_items_for_instance(get_current_user_card_instance());
    popovers.popover_items_handle_keyboard(key, $items);
}

export const default_popover_props = {
    delay: 0,
    appendTo: () => document.body,
    trigger: "click",
    interactive: true,
    hideOnClick: true,
    /* The light-border TippyJS theme is a bit of a misnomer; it
       is a popover styling similar to Bootstrap.  We've also customized
       its CSS to support Zulip's dark theme. */
    theme: "light-border",
    // The maxWidth has been set to "none" to avoid the default value of 300px.
    maxWidth: "none",
    touch: true,
    /* Don't use allow-HTML here since it is unsafe. Instead, use `parse_html`
       to generate the required html */
};

const left_sidebar_tippy_options = {
    placement: "right",
    popperOptions: {
        modifiers: [
            {
                name: "flip",
                options: {
                    fallbackPlacements: "bottom",
                },
            },
        ],
    },
};

export function any_active() {
    return Boolean(get_visible_instance());
}

function on_show_prep(instance) {
    $(instance.popper).on("click", (e) => {
        // Popover is not hidden on click inside it unless the click handler for the
        // element explicitly hides the popover when handling the event.
        // `stopPropagation` is required here to avoid global click handlers from
        // being triggered.
        e.stopPropagation();
    });
    $(instance.popper).one("click", ".navigate_and_close_popover", (e) => {
        // Handler for links inside popover which don't need a special click handler.
        e.stopPropagation();
        instance.hide();
    });
    popovers.hide_all_except_sidebars();
}

export function register_popover_menu(target, popover_props) {
    // For some elements, such as the click target to open the message
    // actions menu, we want to avoid propagating the click event to
    // parent elements. Tippy's built-in `delegate` method does not
    // have an option to do stopPropagation, so we use this method to
    // open the Tippy popovers associated with such elements.
    //
    // A click on the click target will close the menu; for this to
    // work correctly without leaking, all callers need call
    // `instance.destroy()` inside their `onHidden` handler.
    //
    // TODO: Should we instead we wrap the caller's `onHidden` hook,
    // if any, to add `instance.destroy()`?
    $("body").on("click", target, (e) => {
        e.preventDefault();
        e.stopPropagation();
        const instance = e.currentTarget._tippy;

        if (instance) {
            instance.hide();
            return;
        }

        tippy(e.currentTarget, {
            ...default_popover_props,
            showOnCreate: true,
            ...popover_props,
        });
    });
}

export function toggle_message_actions_menu(message) {
    if (message.locally_echoed || message_edit.is_editing(message.id)) {
        // Don't open the popup for locally echoed messages for now.
        // It creates bugs with things like keyboard handlers when
        // we get the server response.
        // We also suppress the popup for messages in an editing state,
        // including previews, when a user tries to reach them from the
        // keyboard.
        return true;
    }

    message_viewport.maybe_scroll_to_show_message_top();
    const $popover_reference = $(".selected_message .actions_hover .zulip-icon-ellipsis-v-solid");
    message_actions_popover_keyboard_toggle = true;
    $popover_reference.trigger("click");
    return true;
}

function set_compose_box_schedule(element) {
    const selected_send_at_time = element.dataset.sendStamp / 1000;
    return selected_send_at_time;
}

export function open_send_later_menu() {
    if (!compose_validate.validate(true)) {
        return;
    }

    // Only show send later options that are possible today.
    const date = new Date();
    const filtered_send_opts = scheduled_messages.get_filtered_send_opts(date);
    $("body").append(render_send_later_modal(filtered_send_opts));
    let interval;

    overlays.open_modal("send_later_modal", {
        autoremove: true,
        on_show() {
            interval = setInterval(
                scheduled_messages.update_send_later_options,
                scheduled_messages.SCHEDULING_MODAL_UPDATE_INTERVAL_IN_MILLISECONDS,
            );

            const $send_later_modal = $("#send_later_modal");

            // Upon the first keydown event, we focus on the first element in the list,
            // enabling keyboard navigation that is handled by `hotkey.js` and `list_util.ts`.
            $send_later_modal.one("keydown", () => {
                const $options = $send_later_modal.find("a");
                $options[0].focus();

                $send_later_modal.on("keydown", (e) => {
                    if (e.key === "Enter") {
                        e.target.click();
                    }
                });
            });

            $send_later_modal.on("click", ".send_later_custom", (e) => {
                const $send_later_modal_content = $send_later_modal.find(".modal__content");
                const current_time = new Date();
                flatpickr.show_flatpickr(
                    $(".send_later_custom")[0],
                    do_schedule_message,
                    new Date(current_time.getTime() + 60 * 60 * 1000),
                    {
                        minDate: new Date(
                            current_time.getTime() +
                                scheduled_messages.MINIMUM_SCHEDULED_MESSAGE_DELAY_SECONDS * 1000,
                        ),
                        onClose() {
                            // Return to normal state.
                            $send_later_modal_content.css("pointer-events", "all");
                        },
                    },
                );
                // Disable interaction with rest of the options in the modal.
                $send_later_modal_content.css("pointer-events", "none");
                e.preventDefault();
                e.stopPropagation();
            });
            $send_later_modal.one(
                "click",
                ".send_later_today, .send_later_tomorrow, .send_later_monday",
                (e) => {
                    const send_at_time = set_compose_box_schedule(e.currentTarget);
                    do_schedule_message(send_at_time);
                    e.preventDefault();
                    e.stopPropagation();
                },
            );
        },
        on_shown() {
            // When shown, we should give the modal focus to correctly handle keyboard events.
            const $send_later_modal_overlay = $("#send_later_modal .modal__overlay");
            $send_later_modal_overlay.trigger("focus");
        },
        on_hide() {
            clearInterval(interval);
        },
    });
}

export function do_schedule_message(send_at_time) {
    overlays.close_modal_if_open("send_later_modal");

    if (!Number.isInteger(send_at_time)) {
        // Convert to timestamp if this is not a timestamp.
        send_at_time = Math.floor(Date.parse(send_at_time) / 1000);
    }
    selected_send_later_timestamp = send_at_time;
    compose.finish(true);
}

export function initialize() {
    register_popover_menu("#streams_inline_icon", {
        onShow(instance) {
            const can_create_streams =
                settings_data.user_can_create_private_streams() ||
                settings_data.user_can_create_public_streams() ||
                settings_data.user_can_create_web_public_streams();

            if (!can_create_streams) {
                // If the user can't create streams, we directly
                // navigate them to the Manage streams subscribe UI.
                window.location.assign("#streams/all");
                // Returning false from an onShow handler cancels the show.
                return false;
            }

            // Assuming that the instance can be shown, track and
            // prep the instance for showing
            popover_instances.stream_settings = instance;
            instance.setContent(parse_html(render_left_sidebar_stream_setting_popover()));
            on_show_prep(instance);

            //  When showing the popover menu, we want the
            // "Add streams" and the "Filter streams" tooltip
            //  to appear below the "Add streams" icon.
            const add_streams_tooltip = $("#add_streams_tooltip").get(0);
            add_streams_tooltip._tippy?.setProps({
                placement: "bottom",
            });
            const filter_streams_tooltip = $("#filter_streams_tooltip").get(0);
            // If `filter_streams_tooltip` is not triggered yet, this will set its initial placement.
            filter_streams_tooltip.dataset.tippyPlacement = "bottom";
            filter_streams_tooltip._tippy?.setProps({
                placement: "bottom",
            });

            // The linter complains about unbalanced returns
            return true;
        },
        onHidden(instance) {
            instance.destroy();
            popover_instances.stream_settings = undefined;
            //  After the popover menu is closed, we want the
            //  "Add streams" and the "Filter streams" tooltip
            //  to appear at it's original position that is
            //  above the "Add streams" icon.
            const add_streams_tooltip = $("#add_streams_tooltip").get(0);
            add_streams_tooltip._tippy?.setProps({
                placement: "top",
            });
            const filter_streams_tooltip = $("#filter_streams_tooltip").get(0);
            filter_streams_tooltip.dataset.tippyPlacement = "top";
            filter_streams_tooltip._tippy?.setProps({
                placement: "top",
            });
        },
    });

    // compose box buttons popover shown on mobile widths.
    // We want this click event to propagate and hide other popovers
    // that could possibly obstruct user from using this popover.
    delegate("body", {
        ...default_popover_props,
        // Attach the click event to `.mobile_button_container`, since
        // the button (`.compose_mobile_button`) already has a hover
        // action attached, for showing the keyboard shortcut,
        // and Tippy cannot handle events that trigger two different
        // actions
        target: ".mobile_button_container",
        placement: "top",
        onShow(instance) {
            popover_instances.compose_mobile_button = instance;
            on_show_prep(instance);
            instance.setContent(
                parse_html(
                    render_mobile_message_buttons_popover_content({
                        is_in_private_narrow: narrow_state.narrowed_to_pms(),
                    }),
                ),
            );
        },
        onMount(instance) {
            const $popper = $(instance.popper);
            $popper.one("click", ".compose_mobile_stream_button", (e) => {
                compose_actions.start("stream", {trigger: "new topic button"});
                e.stopPropagation();
                instance.hide();
            });
            $popper.one("click", ".compose_mobile_private_button", (e) => {
                compose_actions.start("private");
                e.stopPropagation();
                instance.hide();
            });
        },
        onHidden(instance) {
            // Destroy instance so that event handlers
            // are destroyed too.
            instance.destroy();
            popover_instances.compose_control_button = undefined;
        },
    });

    // Click event handlers for it are handled in `compose_ui` and
    // we don't want to close this popover on click inside it but
    // only if user clicked outside it.
    register_popover_menu(".compose_control_menu_wrapper", {
        placement: "top",
        onShow(instance) {
            instance.setContent(
                parse_html(
                    render_compose_control_buttons_popover({
                        giphy_enabled: giphy.is_giphy_enabled(),
                    }),
                ),
            );
            popover_instances.compose_control_buttons = instance;
            popovers.hide_all_except_sidebars();
        },
        onHidden(instance) {
            instance.destroy();
            popover_instances.compose_control_buttons = undefined;
        },
    });

    register_popover_menu("#stream_filters .topic-sidebar-menu-icon", {
        ...left_sidebar_tippy_options,
        onShow(instance) {
            popover_instances.topics_menu = instance;
            on_show_prep(instance);
            const elt = $(instance.reference).closest(".topic-sidebar-menu-icon").expectOne()[0];
            const $stream_li = $(elt).closest(".narrow-filter").expectOne();
            const topic_name = $(elt).closest("li").expectOne().attr("data-topic-name");
            const url = $(elt).closest("li").find(".topic-name").expectOne().prop("href");
            const stream_id = stream_popover.elem_to_stream_id($stream_li);

            instance.context = popover_menus_data.get_topic_popover_content_context({
                stream_id,
                topic_name,
                url,
            });
            instance.setContent(parse_html(render_topic_sidebar_actions(instance.context)));
        },
        onMount(instance) {
            const $popper = $(instance.popper);
            const {stream_id, topic_name} = instance.context;

            if (!stream_id) {
                instance.hide();
                return;
            }

            $popper.one("click", ".sidebar-popover-unmute-topic", () => {
                user_topics.set_user_topic_visibility_policy(
                    stream_id,
                    topic_name,
                    user_topics.all_visibility_policies.UNMUTED,
                );
                instance.hide();
            });

            $popper.one("click", ".sidebar-popover-remove-unmute", () => {
                user_topics.set_user_topic_visibility_policy(
                    stream_id,
                    topic_name,
                    user_topics.all_visibility_policies.INHERIT,
                );
                instance.hide();
            });

            $popper.one("click", ".sidebar-popover-mute-topic", () => {
                user_topics.set_user_topic_visibility_policy(
                    stream_id,
                    topic_name,
                    user_topics.all_visibility_policies.MUTED,
                );
                instance.hide();
            });

            $popper.one("click", ".sidebar-popover-remove-mute", () => {
                user_topics.set_user_topic_visibility_policy(
                    stream_id,
                    topic_name,
                    user_topics.all_visibility_policies.INHERIT,
                );
                instance.hide();
            });

            $popper.one("click", ".sidebar-popover-unstar-all-in-topic", () => {
                starred_messages_ui.confirm_unstar_all_messages_in_topic(
                    Number.parseInt(stream_id, 10),
                    topic_name,
                );
                instance.hide();
            });

            $popper.one("click", ".sidebar-popover-mark-topic-read", () => {
                unread_ops.mark_topic_as_read(stream_id, topic_name);
                instance.hide();
            });

            $popper.one("click", ".sidebar-popover-delete-topic-messages", () => {
                const html_body = render_delete_topic_modal({topic_name});

                confirm_dialog.launch({
                    html_heading: $t_html({defaultMessage: "Delete topic"}),
                    help_link: "/help/delete-a-topic",
                    html_body,
                    on_click() {
                        message_edit.delete_topic(stream_id, topic_name);
                    },
                });

                instance.hide();
            });

            $popper.one("click", ".sidebar-popover-toggle-resolved", () => {
                message_edit.with_first_message_id(stream_id, topic_name, (message_id) => {
                    message_edit.toggle_resolve_topic(message_id, topic_name, true);
                });

                instance.hide();
            });

            $popper.one("click", ".sidebar-popover-move-topic-messages", () => {
                stream_popover.build_move_topic_to_stream_popover(stream_id, topic_name, false);
                instance.hide();
            });

            $popper.one("click", ".sidebar-popover-rename-topic-messages", () => {
                stream_popover.build_move_topic_to_stream_popover(stream_id, topic_name, true);
                instance.hide();
            });

            new ClipboardJS($popper.find(".sidebar-popover-copy-link-to-topic")[0]).on(
                "success",
                () => {
                    instance.hide();
                },
            );
        },
        onHidden(instance) {
            instance.destroy();
            popover_instances.topics_menu = undefined;
        },
    });

    register_popover_menu(".open_enter_sends_dialog", {
        placement: "top",
        onShow(instance) {
            on_show_prep(instance);
            instance.setContent(
                parse_html(
                    render_compose_select_enter_behaviour_popover({
                        enter_sends_true: user_settings.enter_sends,
                    }),
                ),
            );
        },
        onMount(instance) {
            popover_instances.compose_enter_sends = instance;
            common.adjust_mac_kbd_tags(".enter_sends_choices kbd");

            $(instance.popper).one("click", ".enter_sends_choice", (e) => {
                let selected_behaviour = $(e.currentTarget)
                    .find("input[type='radio']")
                    .attr("value");
                selected_behaviour = selected_behaviour === "true"; // Convert to bool
                user_settings.enter_sends = selected_behaviour;
                $(`.enter_sends_${!selected_behaviour}`).hide();
                $(`.enter_sends_${selected_behaviour}`).show();

                // Refocus in the content box so you can continue typing or
                // press Enter to send.
                $("#compose-textarea").trigger("focus");

                channel.patch({
                    url: "/json/settings",
                    data: {enter_sends: selected_behaviour},
                });
                e.stopPropagation();
                instance.hide();
            });
        },
        onHidden(instance) {
            instance.destroy();
            popover_instances.compose_enter_sends = undefined;
        },
    });

    register_popover_menu(".actions_hover .zulip-icon-ellipsis-v-solid", {
        // 320px is our minimum supported width for mobile. We will allow the value to flex
        // to a max of 350px but we shouldn't make the popover wider than this.
        maxWidth: "min(max(320px, 100vw), 350px)",
        placement: "bottom",
        popperOptions: {
            modifiers: [
                {
                    // The placement is set to bottom, but if that placement does not fit,
                    // the opposite top placement will be used.
                    name: "flip",
                    options: {
                        fallbackPlacements: ["top", "left"],
                    },
                },
            ],
        },
        onShow(instance) {
            on_show_prep(instance);
            const $row = $(instance.reference).closest(".message_row");
            const message_id = rows.id($row);
            message_lists.current.select_id(message_id);
            const args = popover_menus_data.get_actions_popover_content_context(message_id);
            instance.setContent(parse_html(render_actions_popover_content(args)));
            $row.addClass("has_popover has_actions_popover");
        },
        onMount(instance) {
            if (message_actions_popover_keyboard_toggle) {
                popovers.focus_first_action_popover_item();
                message_actions_popover_keyboard_toggle = false;
            }
            popover_instances.message_actions = instance;

            // We want click events to propagate to `instance` so that
            // instance.hide gets called.
            const $popper = $(instance.popper);
            $popper.one("click", ".respond_button", (e) => {
                // Arguably, we should fetch the message ID to respond to from
                // e.target, but that should always be the current selected
                // message in the current message list (and
                // compose_actions.respond_to_message doesn't take a message
                // argument).
                compose_actions.quote_and_reply({trigger: "popover respond"});
                e.preventDefault();
                e.stopPropagation();
                instance.hide();
            });

            $popper.one("click", ".popover_edit_message, .popover_view_source", (e) => {
                const message_id = $(e.currentTarget).data("message-id");
                const $row = message_lists.current.get_row(message_id);
                message_edit.start($row);
                e.preventDefault();
                e.stopPropagation();
                instance.hide();
            });

            $popper.one("click", ".popover_move_message", (e) => {
                const message_id = $(e.currentTarget).data("message-id");
                const message = message_lists.current.get(message_id);
                stream_popover.build_move_topic_to_stream_popover(
                    message.stream_id,
                    message.topic,
                    false,
                    message,
                );
                e.preventDefault();
                e.stopPropagation();
                instance.hide();
            });

            $popper.one("click", ".mark_as_unread", (e) => {
                const message_id = $(e.currentTarget).data("message-id");
                unread_ops.mark_as_unread_from_here(message_id);
                e.preventDefault();
                e.stopPropagation();
                instance.hide();
            });

            $popper.one("click", ".popover_toggle_collapse", (e) => {
                const message_id = $(e.currentTarget).data("message-id");
                const $row = message_lists.current.get_row(message_id);
                const message = message_lists.current.get(rows.id($row));
                if ($row) {
                    if (message.collapsed) {
                        condense.uncollapse($row);
                    } else {
                        condense.collapse($row);
                    }
                }
                e.preventDefault();
                e.stopPropagation();
                instance.hide();
            });

            $popper.one("click", ".rehide_muted_user_message", (e) => {
                const message_id = $(e.currentTarget).data("message-id");
                const $row = message_lists.current.get_row(message_id);
                const message = message_lists.current.get(rows.id($row));
                const message_container = message_lists.current.view.message_containers.get(
                    message.id,
                );
                if ($row && !message_container.is_hidden) {
                    message_lists.current.view.hide_revealed_message(message_id);
                }
                e.preventDefault();
                e.stopPropagation();
                instance.hide();
            });

            $popper.one("click", ".view_edit_history", (e) => {
                const message_id = $(e.currentTarget).data("message-id");
                const $row = message_lists.current.get_row(message_id);
                const message = message_lists.current.get(rows.id($row));
                message_edit_history.show_history(message);
                $("#message-history-cancel").trigger("focus");
                e.preventDefault();
                e.stopPropagation();
                instance.hide();
            });

            $popper.one("click", ".view_read_receipts", (e) => {
                const message_id = $(e.currentTarget).data("message-id");
                read_receipts.show_user_list(message_id);
                e.preventDefault();
                e.stopPropagation();
                instance.hide();
            });

            $popper.one("click", ".delete_message", (e) => {
                const message_id = $(e.currentTarget).data("message-id");
                message_edit.delete_message(message_id);
                e.preventDefault();
                e.stopPropagation();
                instance.hide();
            });

            $popper.one("click", ".reaction_button", (e) => {
                const message_id = $(e.currentTarget).data("message-id");
                // Don't propagate the click event since `toggle_emoji_popover` opens a
                // emoji_picker which we don't want to hide after actions popover is hidden.
                e.stopPropagation();
                e.preventDefault();
                emoji_picker.toggle_emoji_popover(
                    instance.reference.parentElement,
                    message_id,
                    true,
                );
                instance.hide();
            });

            new ClipboardJS($popper.find(".copy_link")[0]).on("success", (e) => {
                // e.trigger returns the DOM element triggering the copy action
                const message_id = e.trigger.dataset.messageId;
                const $row = $(`[zid='${CSS.escape(message_id)}']`);
                $row.find(".alert-msg")
                    .text($t({defaultMessage: "Copied!"}))
                    .css("display", "block")
                    .delay(1000)
                    .fadeOut(300);

                setTimeout(() => {
                    // The Clipboard library works by focusing to a hidden textarea.
                    // We unfocus this so keyboard shortcuts, etc., will work again.
                    $(":focus").trigger("blur");
                }, 0);
                instance.hide();
            });
        },
        onHidden(instance) {
            const $row = $(instance.reference).closest(".message_row");
            $row.removeClass("has_popover has_actions_popover");
            instance.destroy();
            popover_instances.message_actions = undefined;
            message_actions_popover_keyboard_toggle = false;
        },
    });

    // Starred messages popover
    register_popover_menu(".starred-messages-sidebar-menu-icon", {
        ...left_sidebar_tippy_options,
        onMount(instance) {
            const $popper = $(instance.popper);
            popover_instances.starred_messages = instance;

            $popper.one("click", "#unstar_all_messages", () => {
                starred_messages_ui.confirm_unstar_all_messages();
                instance.hide();
            });
            $popper.one("click", "#toggle_display_starred_msg_count", () => {
                const data = {};
                const starred_msg_counts = user_settings.starred_message_counts;
                data.starred_message_counts = JSON.stringify(!starred_msg_counts);

                channel.patch({
                    url: "/json/settings",
                    data,
                });
                instance.hide();
            });
        },
        onShow(instance) {
            popovers.hide_all_except_sidebars();
            const show_unstar_all_button = starred_messages.get_count() > 0;

            instance.setContent(
                parse_html(
                    render_starred_messages_sidebar_actions({
                        show_unstar_all_button,
                        starred_message_counts: user_settings.starred_message_counts,
                    }),
                ),
            );
        },
        onHidden(instance) {
            instance.destroy();
            popover_instances.starred_messages = undefined;
        },
    });

    // Drafts popover
    register_popover_menu(".drafts-sidebar-menu-icon", {
        ...left_sidebar_tippy_options,
        onMount(instance) {
            const $popper = $(instance.popper);
            $popper.addClass("drafts-popover");
            popover_instances.drafts = instance;

            $popper.one("click", "#delete_all_drafts_sidebar", () => {
                drafts.confirm_delete_all_drafts();
                instance.hide();
            });
        },
        onShow(instance) {
            popovers.hide_all_except_sidebars();

            instance.setContent(parse_html(render_drafts_sidebar_actions({})));
        },
        onHidden(instance) {
            instance.destroy();
            popover_instances.drafts = undefined;
        },
    });

    // All messages popover
    register_popover_menu(".all-messages-sidebar-menu-icon", {
        ...left_sidebar_tippy_options,
        onMount(instance) {
            const $popper = $(instance.popper);
            $popper.addClass("all-messages-popover");
            popover_instances.all_messages = instance;

            $popper.one("click", "#mark_all_messages_as_read", () => {
                unread_ops.confirm_mark_all_as_read();
                instance.hide();
            });
        },
        onShow(instance) {
            popovers.hide_all_except_sidebars();
            instance.setContent(parse_html(render_all_messages_sidebar_actions()));
        },
        onHidden(instance) {
            instance.destroy();
            popover_instances.all_messages = undefined;
        },
    });

    delegate("body", {
        ...default_popover_props,
        target: "#send_later i",
        onUntrigger() {
            // This is only called when the popover is closed by clicking on `target`.
            $("#compose-textarea").trigger("focus");
        },
        onShow(instance) {
            popovers.hide_all_except_sidebars(instance);
            const formatted_send_later_time = get_formatted_selected_send_later_time();
            instance.setContent(
                parse_html(
                    render_send_later_popover({
                        formatted_send_later_time,
                    }),
                ),
            );
            popover_instances.send_later = instance;
            $(instance.popper).one("click", instance.hide);
        },
        onMount(instance) {
            const $popper = $(instance.popper);
            $popper.one("click", ".send_later_selected_send_later_time", () => {
                const send_at_timestamp = get_selected_send_later_timestamp();
                do_schedule_message(send_at_timestamp);
            });
            $popper.one("click", ".open_send_later_modal", open_send_later_menu);
        },
        onHidden(instance) {
            instance.destroy();
            popover_instances.send_later = undefined;
        },
    });

    function user_card_on_mount(instance, user) {
        popover_menus_data.load_medium_avatar(user, $(".popover-avatar"));
        const $popper = $(instance.popper);
        const $user_name_element = $(".user_full_name");
        if ($user_name_element.prop("clientWidth") < $user_name_element.prop("scrollWidth")) {
            $user_name_element.addClass("tippy-zulip-tooltip");
        }
        popover_menus_data.clipboard_enable($(".copy_mention_syntax")[0]);

        $popper.one("click", ".copy_mention_syntax", () => {
            popovers.hide_all();
        });

        $popper.one("click", ".compose_private_message", (e) => {
            const user_id = popovers.elem_to_user_id($(e.target).parents("nav"));
            const email = people.get_by_user_id(user_id).email;
            compose_actions.start("private", {
                trigger: "popover send private",
                private_message_recipient: email,
            });
            popovers.hide_all();
            if (overlays.is_active()) {
                overlays.close_active();
            }
        });

        $popper.one("click", ".info_popover_actions .narrow_to_private_messages", (e) => {
            const user_id = popovers.elem_to_user_id($(e.target).parents("nav"));
            const email = people.get_by_user_id(user_id).email;
            popovers.hide_all();
            if (overlays.is_active()) {
                overlays.close_active();
            }
            narrow.by("pm-with", email, {trigger: "user sidebar popover"});
        });

        $popper.one("click", ".info_popover_actions .narrow_to_messages_sent", (e) => {
            const user_id = popovers.elem_to_user_id($(e.target).parents("nav"));
            const email = people.get_by_user_id(user_id).email;
            popovers.hide_all();
            if (overlays.is_active()) {
                overlays.close_active();
            }
            narrow.by("sender", email, {trigger: "user sidebar popover"});
        });

        $popper.one("click", ".user_popover .mention_user", (e) => {
            if (!compose_state.composing()) {
                compose_actions.start("stream", {trigger: "sidebar user actions"});
            }
            const user_id = popovers.elem_to_user_id($(e.target).parents("nav"));
            const name = people.get_by_user_id(user_id).full_name;
            const mention = people.get_mention_syntax(name, user_id);
            compose_ui.insert_syntax_and_focus(mention);
            popovers.hide_all();
        });

        $popper.one("click", ".info_popover_actions .clear_status", (e) => {
            e.preventDefault();
            const me = popovers.elem_to_user_id($(e.target).parents("nav"));
            user_status.server_update_status({
                user_id: me,
                status_text: "",
                emoji_name: "",
                emoji_code: "",
            });
            popovers.hide_all();
        });

        $popper.one("click", ".invisible_mode_turn_on", () => {
            popovers.hide_all();
            user_status.server_invisible_mode_on();
        });

        $popper.one("click", ".invisible_mode_turn_off", () => {
            popovers.hide_all();
            user_status.server_invisible_mode_off();
        });

        $popper.one("click", ".bot-owner-name", (e) => {
            show_bot_owner_info_popover(instance, e);
        });

        $popper.one("click", ".update_status_text", popovers.open_user_status_modal);

        $popper.one("click", ".info_popover_actions .view_full_user_profile", (e) => {
            const user_id = popovers.elem_to_user_id($(e.target).parents("nav"));
            const user = people.get_by_user_id(user_id);
            user_profile.show_user_profile(user);
        });
        popover_menus_data.init_email_clipboard();
        popover_menus_data.init_email_tooltip(user);

        $popper.one("click", ".sidebar-popover-manage-user", (e) => {
            e.stopPropagation();
            popovers.hide_all();
            const user_id = popovers.elem_to_user_id($(e.target).parents("nav"));
            const user = people.get_by_user_id(user_id);
            if (user.is_bot) {
                settings_bots.show_edit_bot_info_modal(user_id, true);
            } else {
                settings_users.show_edit_user_info_modal(user_id, true);
            }
        });

        $popper.one("click", ".sidebar-popover-mute-user", (e) => {
            const user_id = popovers.elem_to_user_id($(e.target).parents("nav"));
            popovers.hide_all();

            muted_users_ui.confirm_mute_user(user_id);
        });

        $popper.one("click", ".sidebar-popover-unmute-user", (e) => {
            const user_id = popovers.elem_to_user_id($(e.target).parents("nav"));
            popovers.hide_all();
            muted_users_ui.unmute_user(user_id);
        });

        $popper.one("click", ".sidebar-popover-reactivate-user", (e) => {
            const user_id = popovers.elem_to_user_id($(e.target).parents("nav"));
            popovers.hide_all();

            function handle_confirm() {
                const url = "/json/users/" + encodeURIComponent(user_id) + "/reactivate";
                channel.post({
                    url,
                    success() {
                        dialog_widget.close_modal();
                    },
                    error(xhr) {
                        ui_report.error(
                            $t_html({defaultMessage: "Failed"}),
                            xhr,
                            $("#dialog_error"),
                        );
                        dialog_widget.hide_dialog_spinner();
                    },
                });
            }
            settings_users.confirm_reactivation(user_id, handle_confirm, true);
        });

        $popper.find(".clear_status").each(function () {
            tippy(this, {
                placement: "top",
                appendTo: document.body,
                interactive: true,
            });
        });

        $(".simplebar-content-wrapper").on("scroll", () => {
            instance.hide();
        });
    }

    function placement_on_mobile(instance) {
        if ($("body").outerWidth() < 576) {
            const $overlay = $("<div>").addClass("tippy-overlay").css({
                position: "fixed",
                top: "0",
                left: "0",
                width: "100%",
                height: "100%",
                backgroundColor: "rgba(0, 0, 0, 0.7)",
                zIndex: 9998,
            });

            $("body").append($overlay);
            $overlay.on("click", () => {
                $overlay.remove();
            });
            const $user_card_tippy = $(instance.popper);
            const left = ($("body").innerWidth() - $user_card_tippy.innerWidth()) / 2;
            const top = ($("body").outerHeight() - $user_card_tippy.outerHeight()) / 2;
            $user_card_tippy.css({
                transform: `translate(${left}px, ${top}px)`,
            });
        }
    }
    const user_card_options = {
        arrow: false,
        popperOptions: {
            strategy: "fixed",
            modifiers: [
                {
                    name: "flip",
                    options: {
                        fallbackPlacements: "left",
                    },
                },
            ],
        },
        onShow(instance) {
            const {
                user,
                is_sender_popover = false,
                has_message_context = false,
                template_class = "user_popover",
            } = instance.context;
            on_show_prep(instance);

            const args = popover_menus_data.render_user_info_popover(
                user,
                is_sender_popover,
                has_message_context,
                template_class,
            );

            const $bot_owner_element = $(".bot_owner");
            if (
                args.bot_owner &&
                $bot_owner_element.prop("clientWidth") < $bot_owner_element.prop("scrollWidth")
            ) {
                $bot_owner_element.addClass("tippy-zulip-tooltip");
            }

            const content = $(render_user_info_popover_content(args)).get(0);
            instance.setContent(parse_html(content.innerHTML));
            instance.setProps({
                popperOptions: {
                    strategy: "fixed",
                    modifiers: [
                        {
                            name: "preventOverflow",
                            options: {
                                altAxis: true,
                                padding: {top: 10, bottom: $("#compose").outerHeight()},
                            },
                        },
                        {
                            name: "eventListeners",
                            options: {
                                scroll: false,
                                resize: false,
                            },
                        },
                    ],
                },
            });
        },
        onMount(instance) {
            popover_instances.user_card = instance;
            placement_on_mobile(instance);
            const {user} = instance.context;
            user_card_on_mount(instance, user);
        },
        onHidden(instance) {
            $(".simplebar-content-wrapper").off("scroll");
            instance.destroy();
            popover_instances.user_card = undefined;
            $(".tippy-overlay").remove();
        },
    };

    function show_bot_owner_info_popover(instance, event) {
        instance.hide();
        tippy(instance.reference, {
            ...default_popover_props,
            placement: "right",
            showOnCreate: true,
            onCreate(instance) {
                const participant_user_id = Number.parseInt(
                    $(event.target).attr("data-user-id"),
                    10,
                );
                const user = people.get_by_user_id(participant_user_id);
                instance.context = {user};
            },
            ...user_card_options,
        });
    }

    register_popover_menu(".user-list-sidebar-menu-icon", {
        placement: "left",
        onCreate(instance) {
            const $target = $(instance.reference).closest("li");
            const user_id = popovers.elem_to_user_id($target.find("a"));
            const user = people.get_by_user_id(user_id);
            instance.context = {user, template_class: "sidebar_user_popover"};
        },
        ...user_card_options,
    });

    register_popover_menu(".recent_topics_participant_avatar", {
        placement: "right",
        onCreate(instance) {
            const participant_user_id = Number.parseInt(
                $(instance.reference).parent().attr("data-user-id"),
                10,
            );
            const user = people.get_by_user_id(participant_user_id);
            instance.context = {user};
        },
        ...user_card_options,
    });

    register_popover_menu(".view_user_profile", {
        placement: "right",
        onCreate(instance) {
            const participant_user_id = Number.parseInt(
                $(instance.reference).attr("data-user-id"),
                10,
            );
            const user = people.get_by_user_id(participant_user_id);
            instance.context = {user};
        },
        ...user_card_options,
    });

    const message_user_info_popovers = [".sender_name_user_card", ".profile_picture"];

    for (const target of message_user_info_popovers) {
        register_popover_menu(target, {
            placement: "right",
            onCreate(instance) {
                const $row = $(instance.reference).closest(".message_row");
                const message = message_lists.current.get(rows.id($row));
                const user = people.get_by_user_id(message.sender_id);
                message_lists.current.select_id(message.id);

                if (user === undefined) {
                    // This is never supposed to happen, not even for deactivated
                    // users, so we'll need to debug this error if it occurs.
                    blueslip.error("Bad sender in message" + message.sender_id);
                    return;
                }
                const is_sender_popover = message.sender_id === user.user_id;
                instance.context = {user, is_sender_popover, has_message_context: true};
            },
            ...user_card_options,
        });
    }

    user_card_popover_from_hotkey = function () {
        return tippy(".selected_message", {
            placement: "left",
            appendTo: () => document.body,
            interactive: true,
            theme: "light-border",
            trigger: "manual",
            onCreate(instance) {
                const $row = $(instance.reference).closest(".message_row");
                const message = message_lists.current.get(rows.id($row));
                const user = people.get_by_user_id(message.sender_id);
                message_lists.current.select_id(message.id);

                if (user === undefined) {
                    // This is never supposed to happen, not even for deactivated
                    // users, so we'll need to debug this error if it occurs.
                    blueslip.error("Bad sender in message" + message.sender_id);
                    return;
                }
                const is_sender_popover = message.sender_id === user.user_id;
                instance.context = {user, is_sender_popover, has_message_context: true};
            },
            ...user_card_options,
        })[0];
    };

    register_popover_menu(".user-mention", {
        placement: "right",
        onCreate(instance) {
            const $row = $(instance.reference).closest(".message_row");
            const message = message_lists.current.get(rows.id($row));

            const id_string = $(instance.reference).attr("data-user-id");
            // We fallback to email to handle legacy Markdown that was rendered
            // before we cut over to using data-user-id
            const email = $(instance.reference).attr("data-user-email");
            if (id_string === "*" || email === "*") {
                instance.destroy();
                return;
            }

            let user;
            if (id_string) {
                const user_id = Number.parseInt(id_string, 10);
                user = people.get_by_user_id(user_id);
            } else {
                user = people.get_by_email(email);
            }
            message_lists.current.select_id(message.id);
            const is_sender_popover = message.sender_id === user.user_id;
            instance.context = {user, is_sender_popover, has_message_context: true};
        },
        ...user_card_options,
    });
}
