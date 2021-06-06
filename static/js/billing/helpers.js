import $ from "jquery";

import * as loading from "../loading";
import {page_params} from "../page_params";

export function create_ajax_request(
    url,
    form_name,
    stripe_token = null,
    ignored_inputs = [],
    redirect_to = "/billing",
    type = "POST",
) {
    const form = $(`#${CSS.escape(form_name)}-form`);
    const form_loading_indicator = `#${CSS.escape(form_name)}_loading_indicator`;
    const form_input_section = `#${CSS.escape(form_name)}-input-section`;
    const form_success = `#${CSS.escape(form_name)}-success`;
    const form_error = `#${CSS.escape(form_name)}-error`;
    const form_loading = `#${CSS.escape(form_name)}-loading`;

    const zulip_limited_section = "#zulip-limited-section";
    const free_trial_alert_message = "#free-trial-alert-message";

    loading.make_indicator($(form_loading_indicator), {
        text: "Processing ...",
        abs_positioned: true,
    });
    $(form_input_section).hide();
    $(form_error).hide();
    $(form_loading).show();
    $(zulip_limited_section).hide();
    $(free_trial_alert_message).hide();

    const data = {};
    if (stripe_token) {
        data.stripe_token = stripe_token.id;
    }

    for (const item of form.serializeArray()) {
        if (ignored_inputs.includes(item.name)) {
            continue;
        }
        data[item.name] = item.value;
    }

    $.ajax({
        type,
        url,
        data,
        success() {
            $(form_loading).hide();
            $(form_error).hide();
            $(form_success).show();
            if (["autopay", "invoice"].includes(form_name)) {
                if ("pushState" in history) {
                    history.pushState("", document.title, location.pathname + location.search);
                } else {
                    location.hash = "";
                }
            }
            window.location.replace(redirect_to);
        },
        error(xhr) {
            $(form_loading).hide();
            $(form_error).show().text(JSON.parse(xhr.responseText).msg);
            $(form_input_section).show();
            $(zulip_limited_section).show();
            $(free_trial_alert_message).show();
        },
    });
}

export function format_money(cents) {
    // allow for small floating point errors
    cents = Math.ceil(cents - 0.001);
    let precision;
    if (cents % 100 === 0) {
        precision = 0;
    } else {
        precision = 2;
    }
    // TODO: Add commas for thousands, millions, etc.
    return (cents / 100).toFixed(precision);
}

export function update_charged_amount(prices, schedule) {
    $("#charged_amount").text(format_money(page_params.seat_count * prices[schedule]));
}

export function update_discount_details(organization_type) {
    const discount_details = {
        open_source: "Open source projects are eligible for fully sponsored (free) Zulip Standard.",
        research:
            "Academic research organizations are eligible for fully sponsored (free) Zulip Standard.",
        non_profit: "Nonprofits are eligible for an 85%-100% discount.",
        event: "Events are eligible for fully sponsored (free) Zulip Standard.",
        education: "Education use is eligible for an 85%-100% discount.",
        other: "Your organization might be eligible for a discount or sponsorship.",
    };
    $("#sponsorship-discount-details").text(discount_details[organization_type]);
}

export function show_license_section(license) {
    $("#license-automatic-section").hide();
    $("#license-manual-section").hide();

    $("#automatic_license_count").prop("disabled", true);
    $("#manual_license_count").prop("disabled", true);

    const section_id = `#license-${CSS.escape(license)}-section`;
    $(section_id).show();
    const input_id = `#${CSS.escape(license)}_license_count`;
    $(input_id).prop("disabled", false);
}

let current_page;

function handle_hashchange() {
    $(`#${CSS.escape(current_page)}-tabs.nav a[href="${CSS.escape(location.hash)}"]`).tab("show");
    $("html").scrollTop(0);
}

export function set_tab(page) {
    const hash = location.hash;
    if (hash) {
        $(`#${CSS.escape(page)}-tabs.nav a[href="${CSS.escape(hash)}"]`).tab("show");
        $("html").scrollTop(0);
    }

    $(`#${CSS.escape(page)}-tabs.nav-tabs a`).on("click", function () {
        location.hash = this.hash;
    });

    current_page = page;
    window.addEventListener("hashchange", handle_hashchange);
}

export function is_valid_input(elem) {
    return elem[0].checkValidity();
}
