from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, TypedDict
from urllib.parse import urlencode, urljoin, urlunsplit

from django.conf import settings
from django.db.models import Sum
from django.urls import reverse
from django.utils.timezone import now as timezone_now

from corporate.lib.stripe import (
    BillingSession,
    RemoteRealmBillingSession,
    RemoteServerBillingSession,
)
from corporate.models import (
    Customer,
    CustomerPlan,
    ZulipSponsorshipRequest,
    get_current_plan_by_customer,
)
from zerver.models import Realm
from zerver.models.realms import get_org_type_display_name, get_realm
from zilencer.lib.remote_counts import MissingDataError
from zilencer.models import (
    RemoteCustomerUserCount,
    RemoteInstallationCount,
    RemotePushDeviceToken,
    RemoteRealmCount,
    RemoteZulipServerAuditLog,
    get_remote_realm_guest_and_non_guest_count,
    get_remote_server_guest_and_non_guest_count,
)


class SponsorshipRequestDict(TypedDict):
    org_type: str
    org_website: str
    org_description: str
    total_users: str
    paid_users: str
    paid_users_description: str
    requested_plan: str


@dataclass
class SponsorshipData:
    sponsorship_pending: bool = False
    default_discount: Optional[Decimal] = None
    minimum_licenses: Optional[int] = None
    latest_sponsorship_request: Optional[SponsorshipRequestDict] = None


@dataclass
class PlanData:
    customer: Optional["Customer"] = None
    current_plan: Optional["CustomerPlan"] = None
    next_plan: Optional["CustomerPlan"] = None
    licenses: Optional[int] = None
    licenses_used: Optional[int] = None
    is_legacy_plan: bool = False
    has_fixed_price: bool = False
    warning: Optional[str] = None
    annual_recurring_revenue: Optional[int] = None
    estimated_next_plan_revenue: Optional[int] = None


@dataclass
class MobilePushData:
    mobile_users: Optional[int] = None
    mobile_pushes_forwarded: Optional[int] = None


@dataclass
class SupportData:
    date_created: datetime
    plan_data: PlanData
    sponsorship_data: SponsorshipData
    user_data: RemoteCustomerUserCount
    mobile_push_data: MobilePushData


def get_realm_support_url(realm: Realm) -> str:
    support_realm_uri = get_realm(settings.STAFF_SUBDOMAIN).uri
    support_url = urljoin(
        support_realm_uri,
        urlunsplit(("", "", reverse("support"), urlencode({"q": realm.string_id}), "")),
    )
    return support_url


def get_customer_discount_for_support_view(
    customer: Optional[Customer] = None,
) -> Optional[Decimal]:
    if customer is None:
        return None
    return customer.default_discount


def get_customer_sponsorship_data(customer: Customer) -> SponsorshipData:
    pending = customer.sponsorship_pending
    discount = customer.default_discount
    licenses = customer.minimum_licenses
    sponsorship_request = None
    if pending:
        last_sponsorship_request = (
            ZulipSponsorshipRequest.objects.filter(customer=customer).order_by("id").last()
        )
        if last_sponsorship_request is not None:
            org_type_name = get_org_type_display_name(last_sponsorship_request.org_type)
            if (
                last_sponsorship_request.org_website is None
                or last_sponsorship_request.org_website == ""
            ):
                website = "No website submitted"
            else:
                website = last_sponsorship_request.org_website
            sponsorship_request = SponsorshipRequestDict(
                org_type=org_type_name,
                org_website=website,
                org_description=last_sponsorship_request.org_description,
                total_users=last_sponsorship_request.expected_total_users,
                paid_users=last_sponsorship_request.paid_users_count,
                paid_users_description=last_sponsorship_request.paid_users_description,
                requested_plan=last_sponsorship_request.requested_plan,
            )

    return SponsorshipData(
        sponsorship_pending=pending,
        default_discount=discount,
        minimum_licenses=licenses,
        latest_sponsorship_request=sponsorship_request,
    )


def get_annual_invoice_count(billing_schedule: int) -> int:
    if billing_schedule == CustomerPlan.BILLING_SCHEDULE_MONTHLY:
        return 12
    else:
        return 1


def get_current_plan_data_for_support_view(billing_session: BillingSession) -> PlanData:
    customer = billing_session.get_customer()
    plan = None
    if customer is not None:
        plan = get_current_plan_by_customer(customer)
    plan_data = PlanData(
        customer=customer,
        current_plan=plan,
    )
    if plan is not None:
        new_plan, last_ledger_entry = billing_session.make_end_of_cycle_updates_if_needed(
            plan, timezone_now()
        )
        if last_ledger_entry is not None:
            if new_plan is not None:
                plan_data.current_plan = new_plan  # nocoverage
            plan_data.licenses = last_ledger_entry.licenses
            try:
                plan_data.licenses_used = billing_session.current_count_for_billed_licenses()
            except MissingDataError:  # nocoverage
                plan_data.warning = (
                    "Recent audit log data missing: No information for used licenses"
                )

        assert plan_data.current_plan is not None  # for mypy

        plan_data.next_plan = billing_session.get_next_plan(plan_data.current_plan)

        if plan_data.next_plan is not None:
            if plan_data.next_plan.fixed_price is not None:  # nocoverage
                plan_data.estimated_next_plan_revenue = plan_data.next_plan.fixed_price
            elif plan_data.current_plan.licenses_at_next_renewal() is not None:
                next_plan_licenses = plan_data.current_plan.licenses_at_next_renewal()
                assert next_plan_licenses is not None
                assert plan_data.next_plan.price_per_license is not None
                invoice_count = get_annual_invoice_count(plan_data.next_plan.billing_schedule)
                plan_data.estimated_next_plan_revenue = (
                    plan_data.next_plan.price_per_license * next_plan_licenses * invoice_count
                )
            else:
                plan_data.estimated_next_plan_revenue = 0  # nocoverage

        plan_data.is_legacy_plan = (
            plan_data.current_plan.tier == CustomerPlan.TIER_SELF_HOSTED_LEGACY
        )
        plan_data.has_fixed_price = plan_data.current_plan.fixed_price is not None
        annual_invoice_count = get_annual_invoice_count(plan_data.current_plan.billing_schedule)
        plan_data.annual_recurring_revenue = (
            billing_session.get_customer_plan_renewal_amount(
                plan_data.current_plan, timezone_now(), last_ledger_entry
            )
            * annual_invoice_count
        )

    return plan_data


def get_data_for_support_view(billing_session: BillingSession) -> SupportData:
    if isinstance(billing_session, RemoteServerBillingSession):
        user_data = get_remote_server_guest_and_non_guest_count(billing_session.remote_server.id)
        date_created = RemoteZulipServerAuditLog.objects.get(
            event_type=RemoteZulipServerAuditLog.REMOTE_SERVER_CREATED,
            server__id=billing_session.remote_server.id,
        ).event_time
        mobile_users = (
            RemotePushDeviceToken.objects.filter(server=billing_session.remote_server)
            .distinct("user_id", "user_uuid")
            .count()
        )
        mobile_pushes = RemoteInstallationCount.objects.filter(
            server=billing_session.remote_server,
            property="mobile_pushes_forwarded::day",
            end_time__gte=timezone_now() - timedelta(days=7),
        ).aggregate(total_forwarded=Sum("value", default=0))
        mobile_data = MobilePushData(
            mobile_users=mobile_users, mobile_pushes_forwarded=mobile_pushes["total_forwarded"]
        )
    else:
        assert isinstance(billing_session, RemoteRealmBillingSession)
        user_data = get_remote_realm_guest_and_non_guest_count(billing_session.remote_realm)
        date_created = billing_session.remote_realm.realm_date_created
        mobile_users = (
            RemotePushDeviceToken.objects.filter(remote_realm=billing_session.remote_realm)
            .distinct("user_id", "user_uuid")
            .count()
        )
        mobile_pushes = RemoteRealmCount.objects.filter(
            remote_realm=billing_session.remote_realm,
            property="mobile_pushes_forwarded::day",
            end_time__gte=timezone_now() - timedelta(days=7),
        ).aggregate(total_forwarded=Sum("value", default=0))
        mobile_data = MobilePushData(
            mobile_users=mobile_users, mobile_pushes_forwarded=mobile_pushes["total_forwarded"]
        )
    plan_data = get_current_plan_data_for_support_view(billing_session)
    customer = billing_session.get_customer()
    if customer is not None:
        sponsorship_data = get_customer_sponsorship_data(customer)
    else:
        sponsorship_data = SponsorshipData()

    return SupportData(
        date_created=date_created,
        plan_data=plan_data,
        sponsorship_data=sponsorship_data,
        user_data=user_data,
        mobile_push_data=mobile_data,
    )
