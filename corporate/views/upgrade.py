import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from django import forms
from django.conf import settings
from django.core import signing
from django.db import transaction
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from corporate.lib.stripe import (
    DEFAULT_INVOICE_DAYS_UNTIL_DUE,
    MIN_INVOICED_LICENSES,
    BillingError,
    RealmBillingSession,
    ensure_customer_does_not_have_active_plan,
    get_latest_seat_count,
    is_free_trial_offer_enabled,
    process_initial_upgrade,
    sign_string,
    unsign_string,
    validate_licenses,
)
from corporate.lib.support import get_support_url
from corporate.models import (
    CustomerPlan,
    ZulipSponsorshipRequest,
    get_current_plan_by_customer,
    get_customer_by_realm,
)
from corporate.views.billing_page import billing_home
from zerver.actions.users import do_make_user_billing_admin
from zerver.decorator import require_organization_member, zulip_login_required
from zerver.lib.request import REQ, has_request_variables
from zerver.lib.response import json_success
from zerver.lib.send_email import FromAddress, send_email
from zerver.lib.validator import check_bool, check_int, check_string_in
from zerver.models import UserProfile, get_org_type_display_name

billing_logger = logging.getLogger("corporate.stripe")

VALID_BILLING_MODALITY_VALUES = ["send_invoice", "charge_automatically"]
VALID_BILLING_SCHEDULE_VALUES = ["annual", "monthly"]
VALID_LICENSE_MANAGEMENT_VALUES = ["automatic", "manual"]


def unsign_seat_count(signed_seat_count: str, salt: str) -> int:
    try:
        return int(unsign_string(signed_seat_count, salt))
    except signing.BadSignature:
        raise BillingError("tampered seat count")


def check_upgrade_parameters(
    billing_modality: str,
    schedule: str,
    license_management: Optional[str],
    licenses: Optional[int],
    seat_count: int,
    exempt_from_license_number_check: bool,
) -> None:
    if billing_modality not in VALID_BILLING_MODALITY_VALUES:  # nocoverage
        raise BillingError("unknown billing_modality", "")
    if schedule not in VALID_BILLING_SCHEDULE_VALUES:  # nocoverage
        raise BillingError("unknown schedule")
    if license_management not in VALID_LICENSE_MANAGEMENT_VALUES:  # nocoverage
        raise BillingError("unknown license_management")
    validate_licenses(
        billing_modality == "charge_automatically",
        licenses,
        seat_count,
        exempt_from_license_number_check,
    )


@require_organization_member
@has_request_variables
def upgrade(
    request: HttpRequest,
    user: UserProfile,
    billing_modality: str = REQ(str_validator=check_string_in(VALID_BILLING_MODALITY_VALUES)),
    schedule: str = REQ(str_validator=check_string_in(VALID_BILLING_SCHEDULE_VALUES)),
    signed_seat_count: str = REQ(),
    salt: str = REQ(),
    onboarding: bool = REQ(default=False, json_validator=check_bool),
    license_management: Optional[str] = REQ(
        default=None, str_validator=check_string_in(VALID_LICENSE_MANAGEMENT_VALUES)
    ),
    licenses: Optional[int] = REQ(json_validator=check_int, default=None),
) -> HttpResponse:
    customer = get_customer_by_realm(user.realm)
    if customer is not None:
        ensure_customer_does_not_have_active_plan(customer)
    try:
        seat_count = unsign_seat_count(signed_seat_count, salt)
        if billing_modality == "charge_automatically" and license_management == "automatic":
            licenses = seat_count
        if billing_modality == "send_invoice":
            schedule = "annual"
            license_management = "manual"

        exempt_from_license_number_check = (
            customer is not None and customer.exempt_from_license_number_check
        )
        check_upgrade_parameters(
            billing_modality,
            schedule,
            license_management,
            licenses,
            seat_count,
            exempt_from_license_number_check,
        )
        assert licenses is not None and license_management is not None
        automanage_licenses = license_management == "automatic"
        charge_automatically = billing_modality == "charge_automatically"

        billing_schedule = {"annual": CustomerPlan.ANNUAL, "monthly": CustomerPlan.MONTHLY}[
            schedule
        ]
        if charge_automatically:
            billing_session = RealmBillingSession(user)
            stripe_checkout_session = (
                billing_session.setup_upgrade_checkout_session_and_payment_intent(
                    CustomerPlan.STANDARD,
                    seat_count,
                    licenses,
                    license_management,
                    billing_schedule,
                    billing_modality,
                    onboarding,
                )
            )
            return json_success(
                request,
                data={
                    "stripe_session_url": stripe_checkout_session.url,
                    "stripe_session_id": stripe_checkout_session.id,
                },
            )
        else:
            process_initial_upgrade(
                user,
                CustomerPlan.STANDARD,
                licenses,
                automanage_licenses,
                billing_schedule,
                False,
                is_free_trial_offer_enabled(),
            )
            return json_success(request)

    except BillingError as e:
        billing_logger.warning(
            "BillingError during upgrade: %s. user=%s, realm=%s (%s), billing_modality=%s, "
            "schedule=%s, license_management=%s, licenses=%s",
            e.error_description,
            user.id,
            user.realm.id,
            user.realm.string_id,
            billing_modality,
            schedule,
            license_management,
            licenses,
        )
        raise e
    except Exception:
        billing_logger.exception("Uncaught exception in billing:", stack_info=True)
        error_message = BillingError.CONTACT_SUPPORT.format(email=settings.ZULIP_ADMINISTRATOR)
        error_description = "uncaught exception during upgrade"
        raise BillingError(error_description, error_message)


@zulip_login_required
@has_request_variables
def initial_upgrade(
    request: HttpRequest, onboarding: bool = REQ(default=False, json_validator=check_bool)
) -> HttpResponse:
    user = request.user
    assert user.is_authenticated

    if not settings.BILLING_ENABLED or user.is_guest:
        return render(request, "404.html", status=404)

    customer = get_customer_by_realm(user.realm)
    if (
        customer is not None and customer.sponsorship_pending
    ) or user.realm.plan_type == user.realm.PLAN_TYPE_STANDARD_FREE:
        return HttpResponseRedirect(reverse("sponsorship_request"))

    billing_page_url = reverse(billing_home)
    if customer is not None and (get_current_plan_by_customer(customer) is not None or onboarding):
        if onboarding:
            billing_page_url = f"{billing_page_url}?onboarding=true"
        return HttpResponseRedirect(billing_page_url)

    percent_off = Decimal(0)
    if customer is not None and customer.default_discount is not None:
        percent_off = customer.default_discount

    exempt_from_license_number_check = (
        customer is not None and customer.exempt_from_license_number_check
    )

    seat_count = get_latest_seat_count(user.realm)
    signed_seat_count, salt = sign_string(str(seat_count))
    context: Dict[str, Any] = {
        "realm": user.realm,
        "email": user.delivery_email,
        "seat_count": seat_count,
        "signed_seat_count": signed_seat_count,
        "salt": salt,
        "min_invoiced_licenses": max(seat_count, MIN_INVOICED_LICENSES),
        "default_invoice_days_until_due": DEFAULT_INVOICE_DAYS_UNTIL_DUE,
        "exempt_from_license_number_check": exempt_from_license_number_check,
        "plan": "Zulip Cloud Standard",
        "free_trial_days": settings.FREE_TRIAL_DAYS,
        "onboarding": onboarding,
        "page_params": {
            "seat_count": seat_count,
            "annual_price": 8000,
            "monthly_price": 800,
            "percent_off": float(percent_off),
            "demo_organization_scheduled_deletion_date": user.realm.demo_organization_scheduled_deletion_date,
        },
        "is_demo_organization": user.realm.demo_organization_scheduled_deletion_date is not None,
    }

    response = render(request, "corporate/upgrade.html", context=context)
    return response


class SponsorshipRequestForm(forms.Form):
    website = forms.URLField(max_length=ZulipSponsorshipRequest.MAX_ORG_URL_LENGTH, required=False)
    organization_type = forms.IntegerField()
    description = forms.CharField(widget=forms.Textarea)


@require_organization_member
@has_request_variables
def sponsorship(
    request: HttpRequest,
    user: UserProfile,
    organization_type: str = REQ("organization-type"),
    website: str = REQ(),
    description: str = REQ(),
) -> HttpResponse:
    realm = user.realm
    billing_session = RealmBillingSession(user)

    requested_by = user.full_name
    user_role = user.get_role_name()
    support_url = get_support_url(realm)

    post_data = request.POST.copy()
    # We need to do this because the field name in the template
    # for organization type contains a hyphen and the form expects
    # an underscore.
    post_data.update(organization_type=organization_type)
    form = SponsorshipRequestForm(post_data)

    if form.is_valid():
        with transaction.atomic():
            sponsorship_request = ZulipSponsorshipRequest(
                realm=realm,
                requested_by=user,
                org_website=form.cleaned_data["website"],
                org_description=form.cleaned_data["description"],
                org_type=form.cleaned_data["organization_type"],
            )
            sponsorship_request.save()

            org_type = form.cleaned_data["organization_type"]
            if realm.org_type != org_type:
                realm.org_type = org_type
                realm.save(update_fields=["org_type"])

            billing_session.update_customer_sponsorship_status(True)
            do_make_user_billing_admin(user)

            org_type_display_name = get_org_type_display_name(org_type)

        context = {
            "requested_by": requested_by,
            "user_role": user_role,
            "string_id": realm.string_id,
            "support_url": support_url,
            "organization_type": org_type_display_name,
            "website": website,
            "description": description,
        }
        send_email(
            "zerver/emails/sponsorship_request",
            to_emails=[FromAddress.SUPPORT],
            from_name="Zulip sponsorship",
            from_address=FromAddress.tokenized_no_reply_address(),
            reply_to_email=user.delivery_email,
            context=context,
        )

        return json_success(request)
    else:
        message = " ".join(
            error["message"]
            for error_list in form.errors.get_json_data().values()
            for error in error_list
        )
        raise BillingError("Form validation error", message=message)
