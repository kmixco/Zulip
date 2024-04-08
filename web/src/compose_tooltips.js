import $ from "jquery";
import _ from "lodash";
import {delegate} from "tippy.js";

import render_drafts_tooltip from "../templates/drafts_tooltip.hbs";
import render_narrow_to_compose_recipients_tooltip from "../templates/narrow_to_compose_recipients_tooltip.hbs";

import * as compose_recipient from "./compose_recipient";
import * as compose_state from "./compose_state";
import * as compose_validate from "./compose_validate";
import {$t} from "./i18n";
import * as narrow_state from "./narrow_state";
import * as popover_menus from "./popover_menus";
import {EXTRA_LONG_HOVER_DELAY, LONG_HOVER_DELAY} from "./tippyjs";
import {parse_html} from "./ui_util";
import {user_settings} from "./user_settings";

export function initialize() {
    delegate("body", {
        target: [
            // Ideally this would be `#compose_buttons .button`, but the
            // reply button's actual area is its containing span.
            "#compose_buttons .compose-reply-button-wrapper",
            "#left_bar_compose_mobile_button_big",
            "#new_direct_message_button",
        ],
        delay: EXTRA_LONG_HOVER_DELAY,
        // Only show on mouseenter since for spectators, clicking on these
        // buttons opens login modal, and Micromodal returns focus to the
        // trigger after it closes, which results in tooltip being displayed.
        trigger: "mouseenter",
        appendTo: () => document.body,
        onHidden(instance) {
            instance.destroy();
        },
    });

    delegate("body", {
        target: "#new_conversation_button",
        delay: EXTRA_LONG_HOVER_DELAY,
        // Only show on mouseenter since for spectators, clicking on these
        // buttons opens login modal, and Micromodal returns focus to the
        // trigger after it closes, which results in tooltip being displayed.
        trigger: "mouseenter",
        appendTo: () => document.body,
        onShow(instance) {
            const $elem = $(instance.reference);
            const conversation_type = $elem.attr("data-conversation-type");
            if (conversation_type === "direct") {
                instance.setContent(
                    parse_html($("#new_direct_message_button_tooltip_template").html()),
                );
                return;
            } else if (conversation_type === "stream") {
                instance.setContent(
                    parse_html($("#new_topic_message_button_tooltip_template").html()),
                );
                return;
            }
            // Use new_stream_message_button_tooltip_template when the
            // conversation_type is equal to "non-specific" and also as a default fallback.
            instance.setContent(
                parse_html($("#new_stream_message_button_tooltip_template").html()),
            );
        },
        onHidden(instance) {
            instance.destroy();
        },
    });

    delegate("body", {
        target: ".send-control-button",
        delay: LONG_HOVER_DELAY,
        placement: "top",
        onShow(instance) {
            // Don't show send-area tooltips if the popover is displayed.
            if (popover_menus.is_scheduled_messages_popover_displayed()) {
                return false;
            }
            if (instance.reference.id === "compose-drafts-button") {
                const count =
                    instance.reference.querySelector(".compose-drafts-count").textContent || 0;
                // Explain that the number in brackets is the number of drafts for this conversation.
                const draft_count_msg = $t(
                    {
                        defaultMessage:
                            "{count, plural, one {# draft} other {# drafts}} for this conversation",
                    },
                    {count},
                );
                instance.setContent(parse_html(render_drafts_tooltip({draft_count_msg})));
            }
            return true;
        },
        appendTo: () => document.body,
    });

    delegate("body", {
        target: "#compose-send-button",
        delay: EXTRA_LONG_HOVER_DELAY,
        // By default, tippyjs uses a trigger value of "mouseenter focus",
        // but by specifying "mouseenter", this will prevent showing the
        // Send tooltip when tabbing to the Send button.
        trigger: "mouseenter",
        appendTo: () => document.body,
        onShow(instance) {
            // Don't show Send button tooltip if the popover is displayed.
            if (popover_menus.is_scheduled_messages_popover_displayed()) {
                return false;
            }
            if (user_settings.enter_sends) {
                instance.setContent(parse_html($("#send-enter-tooltip-template").html()));
            } else {
                instance.setContent(parse_html($("#send-ctrl-enter-tooltip-template").html()));
            }
            return true;
        },
    });

    delegate("body", {
        target: ".narrow_to_compose_recipients",
        delay: LONG_HOVER_DELAY,
        appendTo: () => document.body,
        content() {
            const narrow_filter = narrow_state.filter();
            let display_current_view;
            if (narrow_state.is_message_feed_visible()) {
                if (narrow_filter === undefined) {
                    display_current_view = $t({defaultMessage: "Currently viewing all messages."});
                } else if (
                    _.isEqual(narrow_filter.sorted_term_types(), ["stream"]) &&
                    compose_state.get_message_type() === "stream" &&
                    narrow_filter.operands("stream")[0] === compose_state.stream_name()
                ) {
                    display_current_view = $t({
                        defaultMessage: "Currently viewing the entire stream.",
                    });
                } else if (
                    _.isEqual(narrow_filter.sorted_term_types(), ["is-dm"]) &&
                    compose_state.get_message_type() === "private"
                ) {
                    display_current_view = $t({
                        defaultMessage: "Currently viewing all direct messages.",
                    });
                }
            }

            return parse_html(render_narrow_to_compose_recipients_tooltip({display_current_view}));
        },
        onHidden(instance) {
            instance.destroy();
        },
    });

    delegate("body", {
        // TODO: Might need to target just the Send button itself
        // in the new design
        target: [".disabled-message-send-controls"],
        maxWidth: 350,
        content: () =>
            compose_recipient.get_posting_policy_error_message() ||
            compose_validate.get_disabled_send_tooltip(),
        appendTo: () => document.body,
        onHidden(instance) {
            instance.destroy();
        },
    });
}
