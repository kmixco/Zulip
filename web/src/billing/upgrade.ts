import $ from "jquery";
import {z} from "zod";

import {localstorage} from "../localstorage";

import * as helpers from "./helpers";
import type {Prices} from "./helpers";
import {page_params} from "./page_params";

const ls = localstorage();
const ls_selected_schedule = ls.get("selected_schedule");
let selected_schedule: string =
    typeof ls_selected_schedule === "string" ? ls_selected_schedule : "monthly";
let current_license_count = page_params.seat_count;

const upgrade_response_schema = z.object({
    stripe_session_url: z.string().optional(),
    stripe_payment_intent_id: z.string().optional(),
    organization_upgrade_successful: z.boolean().optional(),
});

export const initialize = (): void => {
    $("#org-upgrade-button").on("click", (e) => {
        e.preventDefault();

        // Clear the error box in case this is a repeat request.
        const $error_box = $("#autopay-error");
        $error_box.text("");
        $error_box.hide();

        $("#org-upgrade-button-text").hide();
        $("#org-upgrade-button .upgrade-button-loader").show();
        helpers.create_ajax_request(
            "/json/billing/upgrade",
            "autopay",
            [],
            "POST",
            (response) => {
                const response_data = upgrade_response_schema.parse(response);
                if (response_data.stripe_session_url) {
                    window.location.replace(response_data.stripe_session_url);
                } else if (response_data.stripe_payment_intent_id) {
                    window.location.replace(
                        `/billing/event_status?stripe_payment_intent_id=${response_data.stripe_payment_intent_id}`,
                    );
                } else if (response_data.organization_upgrade_successful) {
                    window.location.replace("/billing");
                }
            },
            () => {
                $("#org-upgrade-button-text").show();
                $("#org-upgrade-button .upgrade-button-loader").hide();
                const error_text = $error_box.text();
                $error_box.text(`${error_text} Please fix this issue or use a different card.`);
            },
        );
    });

    const prices: Prices = {
        annual: page_params.annual_price * (1 - page_params.percent_off / 100),
        monthly: page_params.monthly_price * (1 - page_params.percent_off / 100),
    };

    function update_due_today(schedule: string): void {
        let num_months = 12;
        if (schedule === "monthly") {
            num_months = 1;
        }
        $("#due-today .due-today-duration").text(num_months === 1 ? "1 month" : "12 months");
        const schedule_typed = helpers.schedule_schema.parse(schedule);
        $(".due-today-price").text(
            helpers.format_money(current_license_count * prices[schedule_typed]),
        );
        const unit_price = prices[schedule_typed] / num_months;
        $("#due-today .due-today-unit-price").text(helpers.format_money(unit_price));
    }

    update_due_today(selected_schedule);
    $("#payment-schedule-select").val(selected_schedule);
    $<HTMLInputElement>("#payment-schedule-select").on("change", function () {
        selected_schedule = this.value;
        ls.set("selected_schedule", selected_schedule);
        update_due_today(selected_schedule);
    });

    $("#autopay_annual_price_per_month").text(
        `Pay annually ($${helpers.format_money(prices.annual / 12)}/user/month)`,
    );
    $("#autopay_monthly_price").text(
        `Pay monthly ($${helpers.format_money(prices.monthly)}/user/month)`,
    );

    $<HTMLInputElement>("#manual_license_count").on("keyup", function () {
        $("#upgrade-licenses-change-error").text("");
        const license_count = Number.parseInt(this.value, 10);
        if (!license_count || license_count < page_params.seat_count) {
            $("#upgrade-licenses-change-error").text(
                `You must purchase licenses for all active users in your organization (minimum ${page_params.seat_count}).`,
            );
            return;
        }
        $("#due-today .due-today-license-count").text(license_count);
        const $user_plural = $("#due-today .due-today-license-count-user-plural");
        if (license_count === 1) {
            $user_plural.text("user");
        } else {
            $user_plural.text("users");
        }

        current_license_count = license_count;
        update_due_today(selected_schedule);
    });

    $("#upgrade-add-card-button").on("click", (e) => {
        $("#upgrade-add-card-button #upgrade-add-card-button-text").hide();
        $("#upgrade-add-card-button .loader").show();
        helpers.create_ajax_request(
            "/json/upgrade/session/start_card_update_session",
            "upgrade-cardchange",
            [],
            "POST",
            (response) => {
                const response_data = helpers.stripe_session_url_schema.parse(response);
                window.location.replace(response_data.stripe_session_url);
            },
            () => {
                $("#upgrade-add-card-button .loader").hide();
                $("#upgrade-add-card-button #upgrade-add-card-button-text").show();
            },
        );
        e.preventDefault();
    });
};

$(() => {
    initialize();
});
