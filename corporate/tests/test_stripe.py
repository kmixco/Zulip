import datetime
import mock
import os
from typing import Any, Callable, Dict, List, Optional, TypeVar, Tuple
from functools import wraps, partial
import ujson
import re
import errno
import sys
import operator

from django.core import signing
from django.http import HttpResponse
from django.utils.timezone import utc as timezone_utc
from django.core.management import call_command

import stripe

from zerver.lib.actions import do_deactivate_user, do_create_user, \
    do_activate_user, do_reactivate_user, activity_change_requires_seat_update
from zerver.lib.test_classes import ZulipTestCase
from zerver.lib.timestamp import timestamp_to_datetime, datetime_to_timestamp
from zerver.models import Realm, UserProfile, get_realm, RealmAuditLog
from corporate.lib.stripe import catch_stripe_errors, \
    do_subscribe_customer_to_plan, attach_discount_to_realm, \
    get_seat_count, extract_current_subscription, sign_string, unsign_string, \
    get_next_billing_log_entry, run_billing_processor_one_step, \
    BillingError, StripeCardError, StripeConnectionError
from corporate.models import Customer, Plan, Coupon, BillingProcessor

CallableT = TypeVar('CallableT', bound=Callable[..., Any])

GENERATE_STRIPE_FIXTURES = False

fixture_data_file = open(os.path.join(os.path.dirname(__file__), 'stripe_fixtures.json'), 'r')
fixture_data = ujson.load(fixture_data_file)

def mock_create_customer(*args: Any, **kwargs: Any) -> stripe.Customer:
    return stripe.util.convert_to_stripe_object(fixture_data["create_customer"])

def mock_create_subscription(*args: Any, **kwargs: Any) -> stripe.Subscription:
    return stripe.util.convert_to_stripe_object(fixture_data["create_subscription"])

def mock_customer_with_subscription(*args: Any, **kwargs: Any) -> stripe.Customer:
    return stripe.util.convert_to_stripe_object(fixture_data["customer_with_subscription"])

def mock_customer_with_canceled_subscription(*args: Any, **kwargs: Any) -> stripe.Customer:
    customer = mock_customer_with_subscription()
    customer.subscriptions.data[0].status = "canceled"
    customer.subscriptions.data[0].canceled_at = 1532602160
    return customer

def mock_customer_with_cancel_at_period_end_subscription(*args: Any, **kwargs: Any) -> stripe.Customer:  # nocoverage
    customer = mock_customer_with_subscription()
    customer.subscriptions.data[0].canceled_at = 1532602243
    customer.subscriptions.data[0].cancel_at_period_end = True
    return customer

def mock_customer_with_account_balance(account_balance: int) -> Callable[[str, List[str]], stripe.Customer]:
    def customer_with_account_balance(stripe_customer_id: str, expand: List[str]) -> stripe.Customer:
        stripe_customer = mock_customer_with_subscription()
        stripe_customer.account_balance = account_balance
        return stripe_customer
    return customer_with_account_balance

def mock_upcoming_invoice(*args: Any, **kwargs: Any) -> stripe.Invoice:
    return stripe.util.convert_to_stripe_object(fixture_data["upcoming_invoice"])

def mock_invoice_preview_for_downgrade(total: int=-1000) -> Callable[[str, str, Dict[str, Any]], stripe.Invoice]:
    def invoice_preview(customer: str, subscription: str,
                        subscription_items: Dict[str, Any]) -> stripe.Invoice:
        # TODO: Get a better fixture; this is not at all what these look like
        stripe_invoice = stripe.util.convert_to_stripe_object(fixture_data["upcoming_invoice"])
        stripe_invoice.total = total
        return stripe_invoice
    return invoice_preview

def stripe_fixture_path(decorated_function: CallableT, mocked_function_name: str,
                        call_count: int) -> str:
    fixture_name = "{}:{}".format(decorated_function.__name__, mocked_function_name[7:])
    return "corporate/tests/stripe_fixtures/{}.{}.json".format(fixture_name, call_count)

def generate_and_save_stripe_fixture(decorated_function: CallableT, mocked_function: CallableT,
                                     mocked_function_name: str) -> Callable[[Any, Any], Any]:  # nocoverage
    def _generate_and_save_stripe_fixture(*args: Any, **kwargs: Any) -> Any:
        mock = operator.attrgetter(mocked_function_name)(sys.modules[__name__])
        # Talk to Stripe
        stripe_object = mocked_function(*args, **kwargs)
        filepath = stripe_fixture_path(decorated_function, mocked_function_name, mock.call_count)
        if not os.path.exists(os.path.dirname(filepath)):
            try:
                os.makedirs(os.path.dirname(filepath))
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
        with open(filepath, 'w') as f:
            f.write(str(stripe_object) + "\n")
        return stripe_object
    return _generate_and_save_stripe_fixture

def read_stripe_fixture(decorated_function: CallableT, mocked_function_name: str) -> Callable[[Any, Any], Any]:
    def _read_stripe_fixture(*args: Any, **kwargs: Any) -> Any:
        mock = operator.attrgetter(mocked_function_name)(sys.modules[__name__])
        fixture_file = open(stripe_fixture_path(decorated_function, mocked_function_name, mock.call_count), 'r')
        return stripe.util.convert_to_stripe_object(ujson.load(fixture_file))
    return _read_stripe_fixture

def mock_stripe(mocked_function_name: str, generate_fixture: bool=False) -> Callable[[CallableT], CallableT]:
    def _mock_stripe(decorated_function: CallableT) -> CallableT:
        mocked_function = operator.attrgetter(mocked_function_name)(sys.modules[__name__])
        if GENERATE_STRIPE_FIXTURES or generate_fixture:
            side_effect = generate_and_save_stripe_fixture(decorated_function, mocked_function,
                                                           mocked_function_name)  # nocoverage
        else:
            side_effect = read_stripe_fixture(decorated_function, mocked_function_name)

        @mock.patch(mocked_function_name, side_effect=side_effect)
        @wraps(decorated_function)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            return decorated_function(*args, **kwargs)
        return wrapped
    return _mock_stripe

# A Kandra is a fictional character that can become anything. Used as a
# wildcard when testing for equality.
class Kandra(object):
    def __eq__(self, other: Any) -> bool:
        return True

@mock_stripe("stripe.Coupon.create")
@mock_stripe("stripe.Plan.create")
@mock_stripe("stripe.Product.create")
def setup_stripe(mock_create_product: mock.Mock, mock_create_plan: mock.Mock,
                 mock_create_coupon: mock.Mock) -> None:
    call_command("setup_stripe")

class StripeTest(ZulipTestCase):
    def setUp(self) -> None:
        self.token = 'token'
        # The values below should be copied from stripe_fixtures.json
        self.stripe_customer_id = 'cus_D7OT2jf5YAtZQL'
        self.customer_created = 1529990750
        self.stripe_coupon_id = "rncBblSZ"
        self.stripe_plan_id = 'plan_D7Nh2BtpTvIzYp'
        self.subscription_created = 1529990751
        self.quantity = 8

        self.signed_seat_count, self.salt = sign_string(str(self.quantity))
        Plan.objects.create(nickname=Plan.CLOUD_ANNUAL, stripe_plan_id=self.stripe_plan_id)
        Coupon.objects.create(percent_off=85, stripe_coupon_id=self.stripe_coupon_id)

    def get_signed_seat_count_from_response(self, response: HttpResponse) -> Optional[str]:
        match = re.search(r'name=\"signed_seat_count\" value=\"(.+)\"', response.content.decode("utf-8"))
        return match.group(1) if match else None

    def get_salt_from_response(self, response: HttpResponse) -> Optional[str]:
        match = re.search(r'name=\"salt\" value=\"(\w+)\"', response.content.decode("utf-8"))
        return match.group(1) if match else None

    def create_stripe_token(self) -> stripe.Token:
        return stripe.Token.create(
            card={
                "number": "4242424242424242",
                "exp_month": 3,
                "exp_year": 2033,
                "cvc": "333",
                "name": "Ada Starr",
                "address_line1": "Under the sea,",
                "address_city": "Pacific",
                "address_zip": "33333",
                "address_country": "United States",
            },
        )

    @mock.patch("corporate.lib.stripe.billing_logger.error")
    def test_catch_stripe_errors(self, mock_billing_logger_error: mock.Mock) -> None:
        @catch_stripe_errors
        def raise_invalid_request_error() -> None:
            raise stripe.error.InvalidRequestError(
                "Request req_oJU621i6H6X4Ez: No such token: x", None, json_body={})
        with self.assertRaises(BillingError) as context:
            raise_invalid_request_error()
        self.assertEqual('other stripe error', context.exception.description)
        mock_billing_logger_error.assert_called()

        @catch_stripe_errors
        def raise_card_error() -> None:
            error_message = "The card number is not a valid credit card number."
            json_body = {"error": {"message": error_message}}
            raise stripe.error.CardError(error_message, "number", "invalid_number",
                                         json_body=json_body)
        with self.assertRaises(StripeCardError) as context:
            raise_card_error()
        self.assertIn('not a valid credit card', context.exception.message)
        self.assertEqual('card error', context.exception.description)
        mock_billing_logger_error.assert_called()

    @mock_stripe("stripe.Token.create")
    @mock_stripe("stripe.Customer.retrieve")
    @mock_stripe("stripe.Customer.create")
    @mock_stripe("stripe.Subscription.create")
    def test_initial_upgrade(self, mock_create_subscription: mock.Mock, mock_create_customer: mock.Mock,
                             mock_retrieve_customer: mock.Mock, mock_create_token: mock.Mock) -> None:
        setup_stripe()  # type: ignore # MyPy seems to have trouble recognizing the mock arguments
        user = self.example_user("hamlet")
        self.login(user.email)
        response = self.client_get("/upgrade/")
        self.assert_in_success_response(['We can also bill by invoice'], response)
        self.assertFalse(user.realm.has_seat_based_plan)
        self.assertNotEqual(user.realm.plan_type, Realm.PREMIUM)
        self.assertFalse(Customer.objects.filter(realm=get_realm("zulip")))

        token = self.create_stripe_token()
        # Click "Make payment" in Stripe Checkout
        self.client_post("/upgrade/", {
            'stripeToken': token.id,
            'signed_seat_count': self.get_signed_seat_count_from_response(response),
            'salt': self.get_salt_from_response(response),
            'plan': Plan.CLOUD_ANNUAL})
        # Check that we created a customer and subscription in stripe
        mock_create_customer.assert_called_once_with(
            description="zulip (Zulip Dev)",
            email=user.email,
            metadata={'realm_id': user.realm.id, 'realm_str': 'zulip'},
            source=token.id,
            coupon=None)
        customer = Customer.objects.get(realm=get_realm("zulip"))
        stripe_plan_id = Plan.objects.get(nickname=Plan.CLOUD_ANNUAL).stripe_plan_id
        mock_create_subscription.assert_called_once_with(
            customer=customer.stripe_customer_id,
            billing='charge_automatically',
            items=[{
                'plan': stripe_plan_id,
                'quantity': self.quantity,
            }],
            prorate=True,
            tax_percent=0)
        stripe_customer = stripe.Customer.retrieve(customer.stripe_customer_id)
        subscription = extract_current_subscription(stripe_customer)
        audit_log_entries = list(RealmAuditLog.objects.filter(acting_user=user)
                                 .values_list('event_type', 'event_time').order_by('id'))
        self.assertEqual(audit_log_entries, [
            (RealmAuditLog.STRIPE_CUSTOMER_CREATED, timestamp_to_datetime(stripe_customer.created)),
            (RealmAuditLog.STRIPE_CARD_CHANGED, timestamp_to_datetime(stripe_customer.created)),
            (RealmAuditLog.STRIPE_PLAN_CHANGED, timestamp_to_datetime(subscription.created)),
            (RealmAuditLog.REALM_PLAN_TYPE_CHANGED, Kandra()),
        ])
        # Check that we correctly updated Realm
        realm = get_realm("zulip")
        self.assertTrue(realm.has_seat_based_plan)
        self.assertEqual(realm.plan_type, Realm.PREMIUM)
        self.assertEqual(realm.max_invites, Realm.MAX_INVITES_PREMIUM)
        # Check that we can no longer access /upgrade
        response = self.client_get("/upgrade/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual('/billing/', response.url)

    @mock.patch("stripe.Invoice.upcoming", side_effect=mock_upcoming_invoice)
    @mock.patch("stripe.Customer.retrieve", side_effect=mock_customer_with_subscription)
    @mock.patch("stripe.Customer.create", side_effect=mock_create_customer)
    @mock.patch("stripe.Subscription.create", side_effect=mock_create_subscription)
    def test_billing_page_permissions(self, mock_create_subscription: mock.Mock,
                                      mock_create_customer: mock.Mock,
                                      mock_customer_with_subscription: mock.Mock,
                                      mock_upcoming_invoice: mock.Mock) -> None:
        # Check that non-admins can access /upgrade via /billing, when there is no Customer object
        self.login(self.example_email('hamlet'))
        response = self.client_get("/billing/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual('/upgrade/', response.url)
        # Check that non-admins can sign up and pay
        self.client_post("/upgrade/", {'stripeToken': self.token,
                                       'signed_seat_count': self.signed_seat_count,
                                       'salt': self.salt,
                                       'plan': Plan.CLOUD_ANNUAL})
        # Check that the non-admin hamlet can still access /billing
        response = self.client_get("/billing/")
        self.assert_in_success_response(["for billing history or to make changes"], response)
        # Check admins can access billing, even though they are not a billing admin
        self.login(self.example_email('iago'))
        response = self.client_get("/billing/")
        self.assert_in_success_response(["for billing history or to make changes"], response)
        # Check that a non-admin, non-billing admin user does not have access
        self.login(self.example_email("cordelia"))
        response = self.client_get("/billing/")
        self.assert_in_success_response(["You must be an organization administrator"], response)

    @mock.patch("stripe.Customer.create", side_effect=mock_create_customer)
    @mock.patch("stripe.Subscription.create", side_effect=mock_create_subscription)
    def test_upgrade_with_outdated_seat_count(self, mock_create_subscription: mock.Mock,
                                              mock_create_customer: mock.Mock) -> None:
        self.login(self.example_email("hamlet"))
        new_seat_count = 123
        # Change the seat count while the user is going through the upgrade flow
        response = self.client_get("/upgrade/")
        with mock.patch('corporate.lib.stripe.get_seat_count', return_value=new_seat_count):
            self.client_post("/upgrade/", {
                'stripeToken': self.token,
                'signed_seat_count': self.get_signed_seat_count_from_response(response),
                'salt': self.get_salt_from_response(response),
                'plan': Plan.CLOUD_ANNUAL})
        # Check that the subscription call used the old quantity, not new_seat_count
        mock_create_subscription.assert_called_once_with(
            customer=self.stripe_customer_id,
            billing='charge_automatically',
            items=[{
                'plan': self.stripe_plan_id,
                'quantity': self.quantity,
            }],
            prorate=True,
            tax_percent=0)
        # Check that we have the STRIPE_PLAN_QUANTITY_RESET entry, and that we
        # correctly handled the requires_billing_update field
        audit_log_entries = list(RealmAuditLog.objects.order_by('-id')
                                 .values_list('event_type', 'event_time',
                                              'requires_billing_update')[:5])[::-1]
        self.assertEqual(audit_log_entries, [
            (RealmAuditLog.STRIPE_CUSTOMER_CREATED, timestamp_to_datetime(self.customer_created), False),
            (RealmAuditLog.STRIPE_CARD_CHANGED, timestamp_to_datetime(self.customer_created), False),
            (RealmAuditLog.STRIPE_PLAN_CHANGED, timestamp_to_datetime(self.subscription_created), False),
            (RealmAuditLog.STRIPE_PLAN_QUANTITY_RESET, timestamp_to_datetime(self.subscription_created), True),
            (RealmAuditLog.REALM_PLAN_TYPE_CHANGED, Kandra(), False),
        ])
        self.assertEqual(ujson.loads(RealmAuditLog.objects.filter(
            event_type=RealmAuditLog.STRIPE_PLAN_QUANTITY_RESET).values_list('extra_data', flat=True).first()),
            {'quantity': new_seat_count})

    @mock.patch("stripe.Customer.create", side_effect=mock_create_customer)
    def test_upgrade_where_subscription_save_fails_at_first(self, create_customer: mock.Mock) -> None:
        user = self.example_user("hamlet")
        self.login(user.email)
        with mock.patch('stripe.Subscription.create',
                        side_effect=stripe.error.CardError('message', 'param', 'code', json_body={})):
            self.client_post("/upgrade/", {'stripeToken': self.token,
                                           'signed_seat_count': self.signed_seat_count,
                                           'salt': self.salt,
                                           'plan': Plan.CLOUD_ANNUAL})
        # Check that we created a customer in stripe
        create_customer.assert_called()
        create_customer.reset_mock()
        # Check that we created a Customer with has_billing_relationship=False
        self.assertTrue(Customer.objects.filter(
            stripe_customer_id=self.stripe_customer_id, has_billing_relationship=False).exists())
        # Check that we correctly populated RealmAuditLog
        audit_log_entries = list(RealmAuditLog.objects.filter(acting_user=user)
                                 .values_list('event_type', flat=True).order_by('id'))
        self.assertEqual(audit_log_entries, [RealmAuditLog.STRIPE_CUSTOMER_CREATED,
                                             RealmAuditLog.STRIPE_CARD_CHANGED])
        # Check that we did not update Realm
        realm = get_realm("zulip")
        self.assertFalse(realm.has_seat_based_plan)
        # Check that we still get redirected to /upgrade
        response = self.client_get("/billing/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual('/upgrade/', response.url)

        # mock_create_customer just returns a customer with no subscription object
        with mock.patch("stripe.Subscription.create", side_effect=mock_customer_with_subscription):
            with mock.patch("stripe.Customer.retrieve", side_effect=mock_create_customer):
                with mock.patch("stripe.Customer.save", side_effect=mock_create_customer):
                    self.client_post("/upgrade/", {'stripeToken': self.token,
                                                   'signed_seat_count': self.signed_seat_count,
                                                   'salt': self.salt,
                                                   'plan': Plan.CLOUD_ANNUAL})
        # Check that we do not create a new customer in stripe
        create_customer.assert_not_called()
        # Impossible to create two Customers, but check that we updated has_billing_relationship
        self.assertTrue(Customer.objects.filter(
            stripe_customer_id=self.stripe_customer_id, has_billing_relationship=True).exists())
        # Check that we correctly populated RealmAuditLog
        audit_log_entries = list(RealmAuditLog.objects.filter(acting_user=user)
                                 .values_list('event_type', flat=True).order_by('id'))
        self.assertEqual(audit_log_entries, [RealmAuditLog.STRIPE_CUSTOMER_CREATED,
                                             RealmAuditLog.STRIPE_CARD_CHANGED,
                                             RealmAuditLog.STRIPE_CARD_CHANGED,
                                             RealmAuditLog.STRIPE_PLAN_CHANGED,
                                             RealmAuditLog.REALM_PLAN_TYPE_CHANGED])
        # Check that we correctly updated Realm
        realm = get_realm("zulip")
        self.assertTrue(realm.has_seat_based_plan)
        # Check that we can no longer access /upgrade
        response = self.client_get("/upgrade/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual('/billing/', response.url)

    def test_upgrade_with_tampered_seat_count(self) -> None:
        self.login(self.example_email("hamlet"))
        response = self.client_post("/upgrade/", {
            'stripeToken': self.token,
            'signed_seat_count': "randomsalt",
            'salt': self.salt,
            'plan': Plan.CLOUD_ANNUAL
        })
        self.assert_in_success_response(["Upgrade to Zulip Premium"], response)
        self.assertEqual(response['error_description'], 'tampered seat count')

    def test_upgrade_with_tampered_plan(self) -> None:
        self.login(self.example_email("hamlet"))
        response = self.client_post("/upgrade/", {
            'stripeToken': self.token,
            'signed_seat_count': self.signed_seat_count,
            'salt': self.salt,
            'plan': "invalid"
        })
        self.assert_in_success_response(["Upgrade to Zulip Premium"], response)
        self.assertEqual(response['error_description'], 'tampered plan')

    @mock.patch("stripe.Customer.retrieve", side_effect=mock_customer_with_subscription)
    @mock.patch("stripe.Invoice.upcoming", side_effect=mock_upcoming_invoice)
    def test_billing_home(self, mock_upcoming_invoice: mock.Mock,
                          mock_customer_with_subscription: mock.Mock) -> None:
        user = self.example_user("iago")
        self.login(user.email)
        # No Customer yet; check that we are redirected to /upgrade
        response = self.client_get("/billing/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual('/upgrade/', response.url)

        Customer.objects.create(
            realm=user.realm, stripe_customer_id=self.stripe_customer_id,
            has_billing_relationship=True)

        response = self.client_get("/billing/")
        self.assert_not_in_success_response(['We can also bill by invoice'], response)
        for substring in ['Your plan will renew on', '$%s.00' % (80 * self.quantity,),
                          'Card ending in 4242']:
            self.assert_in_response(substring, response)

    def test_get_seat_count(self) -> None:
        realm = get_realm("zulip")
        initial_count = get_seat_count(realm)
        user1 = UserProfile.objects.create(realm=realm, email='user1@zulip.com', pointer=-1)
        user2 = UserProfile.objects.create(realm=realm, email='user2@zulip.com', pointer=-1)
        self.assertEqual(get_seat_count(realm), initial_count + 2)

        # Test that bots aren't counted
        user1.is_bot = True
        user1.save(update_fields=['is_bot'])
        self.assertEqual(get_seat_count(realm), initial_count + 1)

        # Test that inactive users aren't counted
        do_deactivate_user(user2)
        self.assertEqual(get_seat_count(realm), initial_count)

    def test_extract_current_subscription(self) -> None:
        self.assertIsNone(extract_current_subscription(mock_create_customer()))
        subscription = extract_current_subscription(mock_customer_with_subscription())
        self.assertEqual(subscription["id"][:4], "sub_")
        self.assertIsNone(extract_current_subscription(mock_customer_with_canceled_subscription()))

    def test_subscribe_customer_to_second_plan(self) -> None:
        with self.assertRaisesRegex(BillingError, 'subscribing with existing subscription'):
            do_subscribe_customer_to_plan(self.example_user("iago"),
                                          mock_customer_with_subscription(),
                                          self.stripe_plan_id, self.quantity, 0)

    def test_sign_string(self) -> None:
        string = "abc"
        signed_string, salt = sign_string(string)
        self.assertEqual(string, unsign_string(signed_string, salt))

        with self.assertRaises(signing.BadSignature):
            unsign_string(signed_string, "randomsalt")

    @mock.patch("stripe.Customer.retrieve", side_effect=mock_create_customer)
    @mock.patch("stripe.Customer.create", side_effect=mock_create_customer)
    def test_attach_discount_to_realm(self, mock_create_customer: mock.Mock,
                                      mock_retrieve_customer: mock.Mock) -> None:
        user = self.example_user('hamlet')
        # Before customer exists
        attach_discount_to_realm(user, 85)
        mock_create_customer.assert_called_once_with(
            description=Kandra(), email=self.example_email('hamlet'), metadata=Kandra(),
            source=None, coupon=self.stripe_coupon_id)
        mock_create_customer.reset_mock()
        # For existing customer
        Coupon.objects.create(percent_off=25, stripe_coupon_id='25OFF')
        with mock.patch.object(
                stripe.Customer, 'save', autospec=True,
                side_effect=lambda stripe_customer: self.assertEqual(stripe_customer.coupon, '25OFF')):
            attach_discount_to_realm(user, 25)
        mock_create_customer.assert_not_called()

    @mock.patch("stripe.Subscription.delete")
    @mock.patch("stripe.Customer.save")
    @mock.patch("stripe.Invoice.upcoming", side_effect=mock_invoice_preview_for_downgrade())
    @mock.patch("stripe.Customer.retrieve", side_effect=mock_customer_with_subscription)
    def test_downgrade(self, mock_retrieve_customer: mock.Mock, mock_upcoming_invoice: mock.Mock,
                       mock_save_customer: mock.Mock, mock_delete_subscription: mock.Mock) -> None:
        realm = get_realm('zulip')
        realm.has_seat_based_plan = True
        realm.plan_type = Realm.PREMIUM
        realm.save(update_fields=['has_seat_based_plan', 'plan_type'])
        Customer.objects.create(
            realm=realm, stripe_customer_id=self.stripe_customer_id, has_billing_relationship=True)
        user = self.example_user('iago')
        self.login(user.email)
        response = self.client_post("/json/billing/downgrade", {})
        self.assert_json_success(response)

        mock_delete_subscription.assert_called()
        mock_save_customer.assert_called()
        realm = get_realm('zulip')
        self.assertFalse(realm.has_seat_based_plan)
        audit_log_entries = list(RealmAuditLog.objects.filter(acting_user=user)
                                 .values_list('event_type', flat=True).order_by('id'))
        # TODO: once we have proper mocks, test for event_time and extra_data in STRIPE_PLAN_CHANGED
        self.assertEqual(audit_log_entries, [RealmAuditLog.STRIPE_PLAN_CHANGED,
                                             RealmAuditLog.REALM_PLAN_TYPE_CHANGED])
        self.assertEqual(realm.plan_type, Realm.LIMITED)

    @mock.patch("stripe.Customer.save")
    @mock.patch("stripe.Customer.retrieve", side_effect=mock_create_customer)
    def test_downgrade_with_no_subscription(
            self, mock_retrieve_customer: mock.Mock, mock_save_customer: mock.Mock) -> None:
        realm = get_realm('zulip')
        Customer.objects.create(
            realm=realm, stripe_customer_id=self.stripe_customer_id, has_billing_relationship=True)
        self.login(self.example_email('iago'))
        response = self.client_post("/json/billing/downgrade", {})
        self.assert_json_error_contains(response, 'Please reload')
        self.assertEqual(ujson.loads(response.content)['error_description'], 'downgrade without subscription')
        mock_save_customer.assert_not_called()

    def test_downgrade_permissions(self) -> None:
        self.login(self.example_email('hamlet'))
        response = self.client_post("/json/billing/downgrade", {})
        self.assert_json_error_contains(response, "Access denied")
        # billing admin but not realm admin
        user = self.example_user('hamlet')
        user.is_billing_admin = True
        user.save(update_fields=['is_billing_admin'])
        with mock.patch('corporate.views.process_downgrade') as mocked1:
            self.client_post("/json/billing/downgrade", {})
        mocked1.assert_called()
        # realm admin but not billing admin
        user = self.example_user('hamlet')
        user.is_billing_admin = False
        user.is_realm_admin = True
        user.save(update_fields=['is_billing_admin', 'is_realm_admin'])
        with mock.patch('corporate.views.process_downgrade') as mocked2:
            self.client_post("/json/billing/downgrade", {})
        mocked2.assert_called()

    @mock.patch("stripe.Subscription.delete")
    @mock.patch("stripe.Customer.retrieve", side_effect=mock_customer_with_account_balance(1234))
    def test_downgrade_credits(self, mock_retrieve_customer: mock.Mock,
                               mock_delete_subscription: mock.Mock) -> None:
        user = self.example_user('iago')
        self.login(user.email)
        Customer.objects.create(
            realm=user.realm, stripe_customer_id=self.stripe_customer_id, has_billing_relationship=True)
        # Check that positive balance is forgiven
        with mock.patch("stripe.Invoice.upcoming", side_effect=mock_invoice_preview_for_downgrade(1000)):
            with mock.patch.object(
                    stripe.Customer, 'save', autospec=True,
                    side_effect=lambda customer: self.assertEqual(customer.account_balance, 1234)):
                response = self.client_post("/json/billing/downgrade", {})
        self.assert_json_success(response)
        # Check that negative balance is credited
        with mock.patch("stripe.Invoice.upcoming", side_effect=mock_invoice_preview_for_downgrade(-1000)):
            with mock.patch.object(
                    stripe.Customer, 'save', autospec=True,
                    side_effect=lambda customer: self.assertEqual(customer.account_balance, 234)):
                response = self.client_post("/json/billing/downgrade", {})
        self.assert_json_success(response)

    @mock.patch("stripe.Customer.retrieve", side_effect=mock_customer_with_subscription)
    def test_replace_payment_source(self, mock_retrieve_customer: mock.Mock) -> None:
        user = self.example_user("iago")
        self.login(user.email)
        Customer.objects.create(realm=user.realm, stripe_customer_id=self.stripe_customer_id)
        with mock.patch.object(stripe.Customer, 'save', autospec=True,
                               side_effect=lambda customer: self.assertEqual(customer.source, "new_token")):
            result = self.client_post("/json/billing/sources/change",
                                      {'stripe_token': ujson.dumps("new_token")})
        self.assert_json_success(result)
        log_entry = RealmAuditLog.objects.order_by('-id').first()
        self.assertEqual(user, log_entry.acting_user)
        self.assertEqual(RealmAuditLog.STRIPE_CARD_CHANGED, log_entry.event_type)

    def test_update_payment_source_permissions(self) -> None:
        # This can be removed / merged with e.g. test_downgrade_permissions
        # once we have a decorator that handles billing page permissions
        self.login(self.example_email('hamlet'))
        response = self.client_post("/json/billing/sources/change",
                                    {'stripe_token': ujson.dumps('token')})
        self.assert_json_error_contains(response, "Access denied")
        # billing admin but not realm admin
        user = self.example_user('hamlet')
        user.is_billing_admin = True
        user.save(update_fields=['is_billing_admin'])
        with mock.patch('corporate.views.do_replace_payment_source') as mocked1:
            self.client_post("/json/billing/sources/change",
                             {'stripe_token': ujson.dumps('token')})
        mocked1.assert_called()
        # realm admin but not billing admin
        user = self.example_user('hamlet')
        user.is_billing_admin = False
        user.is_realm_admin = True
        user.save(update_fields=['is_billing_admin', 'is_realm_admin'])
        with mock.patch('corporate.views.do_replace_payment_source') as mocked2:
            self.client_post("/json/billing/sources/change",
                             {'stripe_token': ujson.dumps('token')})
        mocked2.assert_called()

    @mock.patch("stripe.Customer.create", side_effect=mock_create_customer)
    @mock.patch("stripe.Subscription.create", side_effect=mock_create_subscription)
    @mock.patch("stripe.Customer.retrieve", side_effect=mock_customer_with_subscription)
    def test_billing_quantity_changes_end_to_end(
            self, mock_customer_with_subscription: mock.Mock, mock_create_subscription: mock.Mock,
            mock_create_customer: mock.Mock) -> None:
        self.login(self.example_email("hamlet"))
        processor = BillingProcessor.objects.create(
            log_row=RealmAuditLog.objects.order_by('id').first(), state=BillingProcessor.DONE)

        def check_billing_processor_update(event_type: str, quantity: int) -> None:
            def check_subscription_save(subscription: stripe.Subscription, idempotency_key: str) -> None:
                self.assertEqual(subscription.quantity, quantity)
                log_row = RealmAuditLog.objects.filter(
                    event_type=event_type, requires_billing_update=True).order_by('-id').first()
                self.assertEqual(idempotency_key, 'process_billing_log_entry:%s' % (log_row.id,))
                self.assertEqual(subscription.proration_date, datetime_to_timestamp(log_row.event_time))
            with mock.patch.object(stripe.Subscription, 'save', autospec=True,
                                   side_effect=check_subscription_save):
                run_billing_processor_one_step(processor)

        # Test STRIPE_PLAN_QUANTITY_RESET
        new_seat_count = 123
        # change the seat count while the user is going through the upgrade flow
        with mock.patch('corporate.lib.stripe.get_seat_count', return_value=new_seat_count):
            self.client_post("/upgrade/", {'stripeToken': self.token,
                                           'signed_seat_count': self.signed_seat_count,
                                           'salt': self.salt,
                                           'plan': Plan.CLOUD_ANNUAL})
        check_billing_processor_update(RealmAuditLog.STRIPE_PLAN_QUANTITY_RESET, new_seat_count)

        # Test USER_CREATED
        user = do_create_user('newuser@zulip.com', 'password', get_realm('zulip'), 'full name', 'short name')
        check_billing_processor_update(RealmAuditLog.USER_CREATED, self.quantity + 1)

        # Test USER_DEACTIVATED
        do_deactivate_user(user)
        check_billing_processor_update(RealmAuditLog.USER_DEACTIVATED, self.quantity - 1)

        # Test USER_REACTIVATED
        do_reactivate_user(user)
        check_billing_processor_update(RealmAuditLog.USER_REACTIVATED, self.quantity + 1)

        # Test USER_ACTIVATED
        # Not a proper use of do_activate_user, but it's fine to call it like this for this test
        do_activate_user(user)
        check_billing_processor_update(RealmAuditLog.USER_ACTIVATED, self.quantity + 1)

class RequiresBillingUpdateTest(ZulipTestCase):
    def test_activity_change_requires_seat_update(self) -> None:
        # Realm doesn't have a seat based plan
        self.assertFalse(activity_change_requires_seat_update(self.example_user("hamlet")))
        realm = get_realm("zulip")
        realm.has_seat_based_plan = True
        realm.save(update_fields=['has_seat_based_plan'])
        # seat based plan + user not a bot
        user = self.example_user("hamlet")
        self.assertTrue(activity_change_requires_seat_update(user))
        user.is_bot = True
        user.save(update_fields=['is_bot'])
        # seat based plan but user is a bot
        self.assertFalse(activity_change_requires_seat_update(user))

    def test_requires_billing_update_for_is_active_changes(self) -> None:
        count = RealmAuditLog.objects.count()
        realm = get_realm("zulip")
        user1 = do_create_user('user1@zulip.com', 'password', realm, 'full name', 'short name')
        do_deactivate_user(user1)
        do_reactivate_user(user1)
        # Not a proper use of do_activate_user, but it's fine to call it like this for this test
        do_activate_user(user1)
        self.assertEqual(count + 4,
                         RealmAuditLog.objects.filter(requires_billing_update=False).count())

        realm.has_seat_based_plan = True
        realm.save(update_fields=['has_seat_based_plan'])
        user2 = do_create_user('user2@zulip.com', 'password', realm, 'full name', 'short name')
        do_deactivate_user(user2)
        do_reactivate_user(user2)
        do_activate_user(user2)
        self.assertEqual(4, RealmAuditLog.objects.filter(requires_billing_update=True).count())

class BillingProcessorTest(ZulipTestCase):
    def add_log_entry(self, realm: Realm=get_realm('zulip'),
                      event_type: str=RealmAuditLog.USER_CREATED,
                      requires_billing_update: bool=True) -> RealmAuditLog:
        return RealmAuditLog.objects.create(
            realm=realm, event_time=datetime.datetime(2001, 2, 3, 4, 5, 6).replace(tzinfo=timezone_utc),
            event_type=event_type, requires_billing_update=requires_billing_update)

    def test_get_next_billing_log_entry(self) -> None:
        second_realm = Realm.objects.create(string_id='second', name='second')
        entry1 = self.add_log_entry(realm=second_realm)
        realm_processor = BillingProcessor.objects.create(
            realm=second_realm, log_row=entry1, state=BillingProcessor.DONE)
        entry2 = self.add_log_entry()
        # global processor
        processor = BillingProcessor.objects.create(
            log_row=entry2, state=BillingProcessor.STARTED)

        # Test STARTED, STALLED, and typo'ed state entry
        self.assertEqual(entry2, get_next_billing_log_entry(processor))
        processor.state = BillingProcessor.STALLED
        processor.save()
        with self.assertRaises(AssertionError):
            get_next_billing_log_entry(processor)
        processor.state = 'typo'
        processor.save()
        with self.assertRaisesRegex(BillingError, 'unknown processor state'):
            get_next_billing_log_entry(processor)

        # Test global processor is handled correctly
        processor.state = BillingProcessor.DONE
        processor.save()
        # test it ignores entries with requires_billing_update=False
        entry3 = self.add_log_entry(requires_billing_update=False)
        # test it ignores entries with realm processors
        entry4 = self.add_log_entry(realm=second_realm)
        self.assertIsNone(get_next_billing_log_entry(processor))
        # test it does catch entries it should
        entry5 = self.add_log_entry()
        self.assertEqual(entry5, get_next_billing_log_entry(processor))

        # Test realm processor is handled correctly
        # test it gets the entry with its realm, and ignores the entry with
        # requires_billing_update=False, when global processor is up ahead
        processor.log_row = entry5
        processor.save()
        self.assertEqual(entry4, get_next_billing_log_entry(realm_processor))

        # test it doesn't run past the global processor
        processor.log_row = entry3
        processor.save()
        self.assertIsNone(get_next_billing_log_entry(realm_processor))

    def test_run_billing_processor_logic_when_no_errors(self) -> None:
        second_realm = Realm.objects.create(string_id='second', name='second')
        entry1 = self.add_log_entry(realm=second_realm)
        realm_processor = BillingProcessor.objects.create(
            realm=second_realm, log_row=entry1, state=BillingProcessor.DONE)
        entry2 = self.add_log_entry()
        # global processor
        processor = BillingProcessor.objects.create(
            log_row=entry2, state=BillingProcessor.DONE)

        # Test nothing to process
        # test nothing changes, for global processor
        self.assertFalse(run_billing_processor_one_step(processor))
        self.assertEqual(2, BillingProcessor.objects.count())
        # test realm processor gets deleted
        self.assertFalse(run_billing_processor_one_step(realm_processor))
        self.assertEqual(1, BillingProcessor.objects.count())
        self.assertEqual(1, BillingProcessor.objects.filter(realm=None).count())

        # Test something to process
        processor.state = BillingProcessor.STARTED
        processor.save()
        realm_processor = BillingProcessor.objects.create(
            realm=second_realm, log_row=entry1, state=BillingProcessor.STARTED)
        Customer.objects.create(realm=get_realm('zulip'), stripe_customer_id='cust_1')
        Customer.objects.create(realm=second_realm, stripe_customer_id='cust_2')
        with mock.patch('corporate.lib.stripe.do_adjust_subscription_quantity'):
            # test return values
            self.assertTrue(run_billing_processor_one_step(processor))
            self.assertTrue(run_billing_processor_one_step(realm_processor))
        # test no processors get added or deleted
        self.assertEqual(2, BillingProcessor.objects.count())

    @mock.patch("corporate.lib.stripe.billing_logger.error")
    def test_run_billing_processor_with_card_error(self, mock_billing_logger_error: mock.Mock) -> None:
        second_realm = Realm.objects.create(string_id='second', name='second')
        entry1 = self.add_log_entry(realm=second_realm)
        # global processor
        processor = BillingProcessor.objects.create(
            log_row=entry1, state=BillingProcessor.STARTED)
        Customer.objects.create(realm=second_realm, stripe_customer_id='cust_2')

        # card error on global processor should create a new realm processor
        with mock.patch('corporate.lib.stripe.do_adjust_subscription_quantity',
                        side_effect=stripe.error.CardError('message', 'param', 'code', json_body={})):
            self.assertTrue(run_billing_processor_one_step(processor))
        self.assertEqual(2, BillingProcessor.objects.count())
        self.assertTrue(BillingProcessor.objects.filter(
            realm=None, log_row=entry1, state=BillingProcessor.SKIPPED).exists())
        self.assertTrue(BillingProcessor.objects.filter(
            realm=second_realm, log_row=entry1, state=BillingProcessor.STALLED).exists())
        mock_billing_logger_error.assert_called()

        # card error on realm processor should change state to STALLED
        realm_processor = BillingProcessor.objects.filter(realm=second_realm).first()
        realm_processor.state = BillingProcessor.STARTED
        realm_processor.save()
        with mock.patch('corporate.lib.stripe.do_adjust_subscription_quantity',
                        side_effect=stripe.error.CardError('message', 'param', 'code', json_body={})):
            self.assertTrue(run_billing_processor_one_step(realm_processor))
        self.assertEqual(2, BillingProcessor.objects.count())
        self.assertTrue(BillingProcessor.objects.filter(
            realm=second_realm, log_row=entry1, state=BillingProcessor.STALLED).exists())
        mock_billing_logger_error.assert_called()

    @mock.patch("corporate.lib.stripe.billing_logger.error")
    def test_run_billing_processor_with_uncaught_error(self, mock_billing_logger_error: mock.Mock) -> None:
        # This tests three different things:
        # * That run_billing_processor_one_step passes through exceptions that
        #   are not StripeCardError
        # * That process_billing_log_entry catches StripeErrors and re-raises them as BillingErrors
        # * That processor.state=STARTED for non-StripeCardError exceptions
        entry1 = self.add_log_entry()
        entry2 = self.add_log_entry()
        processor = BillingProcessor.objects.create(
            log_row=entry1, state=BillingProcessor.DONE)
        Customer.objects.create(realm=get_realm('zulip'), stripe_customer_id='cust_1')
        with mock.patch('corporate.lib.stripe.do_adjust_subscription_quantity',
                        side_effect=stripe.error.StripeError('message', 'param', 'code', json_body={})):
            with self.assertRaises(BillingError):
                run_billing_processor_one_step(processor)
        mock_billing_logger_error.assert_called()
        # check processor.state is STARTED
        self.assertTrue(BillingProcessor.objects.filter(
            log_row=entry2, state=BillingProcessor.STARTED).exists())
