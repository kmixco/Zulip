# -*- coding: utf-8 -*-
from django.test import TestCase
from django.utils.translation import ugettext as _
from django.http import HttpResponse

from zerver.tests.test_hooks import WebhookTestCase

from zerver.lib.actions import do_deactivate_realm, do_deactivate_user, \
    do_reactivate_user, do_reactivate_realm
from zerver.lib.test_helpers import (
    AuthedTestCase,
)
from zerver.lib.request import \
    REQ, has_request_variables, RequestVariableMissingError, \
    RequestVariableConversionError, JsonableError
from zerver.decorator import \
    api_key_only_webhook_view,\
    authenticated_json_post_view, authenticated_json_view,\
    validate_api_key
from zerver.lib.validator import (
    check_string, check_dict, check_bool, check_int, check_list
)
from zerver.models import \
    get_realm, get_user_profile_by_email

import ujson

class DecoratorTestCase(TestCase):
    def test_REQ_converter(self):

        def my_converter(data):
            lst = ujson.loads(data)
            if not isinstance(lst, list):
                raise ValueError('not a list')
            if 13 in lst:
                raise JsonableError(_('13 is an unlucky number!'))
            return lst

        @has_request_variables
        def get_total(request, numbers=REQ(converter=my_converter)):
            return sum(numbers)

        class Request(object):
            REQUEST = {} # type: Dict[str, str]

        request = Request()

        with self.assertRaises(RequestVariableMissingError):
            get_total(request)

        request.REQUEST['numbers'] = 'bad_value'
        with self.assertRaises(RequestVariableConversionError) as cm:
            get_total(request)
        self.assertEqual(str(cm.exception), "Bad value for 'numbers': bad_value")

        request.REQUEST['numbers'] = ujson.dumps([2, 3, 5, 8, 13, 21])
        with self.assertRaises(JsonableError) as cm:
            get_total(request)
        self.assertEqual(str(cm.exception), "13 is an unlucky number!")

        request.REQUEST['numbers'] = ujson.dumps([1, 2, 3, 4, 5, 6])
        result = get_total(request)
        self.assertEqual(result, 21)

    def test_REQ_validator(self):

        @has_request_variables
        def get_total(request, numbers=REQ(validator=check_list(check_int))):
            return sum(numbers)

        class Request(object):
            REQUEST = {} # type: Dict[str, str]

        request = Request()

        with self.assertRaises(RequestVariableMissingError):
            get_total(request)

        request.REQUEST['numbers'] = 'bad_value'
        with self.assertRaises(JsonableError) as cm:
            get_total(request)
        self.assertEqual(str(cm.exception), 'argument "numbers" is not valid json.')

        request.REQUEST['numbers'] = ujson.dumps([1, 2, "what?", 4, 5, 6])
        with self.assertRaises(JsonableError) as cm:
            get_total(request)
        self.assertEqual(str(cm.exception), 'numbers[2] is not an integer')

        request.REQUEST['numbers'] = ujson.dumps([1, 2, 3, 4, 5, 6])
        result = get_total(request)
        self.assertEqual(result, 21)

    def test_REQ_argument_type(self):

        @has_request_variables
        def get_payload(request, payload=REQ(argument_type='body')):
            return payload

        class MockRequest(object):
            body = {}

        request = MockRequest()

        request.body = 'notjson'
        with self.assertRaises(JsonableError) as cm:
            get_payload(request)
        self.assertEqual(str(cm.exception), 'Malformed JSON')

        request.body = '{"a": "b"}'
        self.assertEqual(get_payload(request), {'a': 'b'})

        # Test we properly handle an invalid argument_type.
        with self.assertRaises(Exception) as cm:
            @has_request_variables
            def test(request, payload=REQ(argument_type="invalid")):
                pass
            test(request)

    def test_api_key_only_webhook_view(self):
        @api_key_only_webhook_view('ClientName')
        def get_user_profile_api_key(request, user_profile, client):
            return user_profile.api_key

        class Request(object):
            REQUEST = {} # type: Dict[str, str]
            COOKIES = {}
            META = {'PATH_INFO': ''}

        webhook_bot_email = 'webhook-bot@zulip.com'
        request = Request()

        request.REQUEST['api_key'] = 'not_existing_api_key'
        with self.assertRaises(JsonableError):
            get_user_profile_api_key(request)

        request.REQUEST['api_key'] = get_user_profile_by_email(webhook_bot_email).api_key
        self.assertEqual(get_user_profile_api_key(request), get_user_profile_by_email(webhook_bot_email).api_key)

class ValidatorTestCase(TestCase):
    def test_check_string(self):
        x = "hello"
        self.assertEqual(check_string('x', x), None)

        x = 4
        self.assertEqual(check_string('x', x), 'x is not a string')

    def test_check_bool(self):
        x = True
        self.assertEqual(check_bool('x', x), None)

        x = 4
        self.assertEqual(check_bool('x', x), 'x is not a boolean')

    def test_check_int(self):
        x = 5
        self.assertEqual(check_int('x', x), None)

        x = [{}]
        self.assertEqual(check_int('x', x), 'x is not an integer')

    def test_check_list(self):
        x = 999
        error = check_list(check_string)('x', x)
        self.assertEqual(error, 'x is not a list')

        x = ["hello", 5]
        error = check_list(check_string)('x', x)
        self.assertEqual(error, 'x[1] is not a string')

        x = [["yo"], ["hello", "goodbye", 5]]
        error = check_list(check_list(check_string))('x', x)
        self.assertEqual(error, 'x[1][2] is not a string')

        x = ["hello", "goodbye", "hello again"]
        error = check_list(check_string, length=2)('x', x)
        self.assertEqual(error, 'x should have exactly 2 items')

    def test_check_dict(self):
        keys = [
            ('names', check_list(check_string)),
            ('city', check_string),
        ]

        x = {
            'names': ['alice', 'bob'],
            'city': 'Boston',
        }
        error = check_dict(keys)('x', x)
        self.assertEqual(error, None)

        x = 999
        error = check_dict(keys)('x', x)
        self.assertEqual(error, 'x is not a dict')

        x = {}
        error = check_dict(keys)('x', x)
        self.assertEqual(error, 'names key is missing from x')

        x = {
            'names': ['alice', 'bob', {}]
        }
        error = check_dict(keys)('x', x)
        self.assertEqual(error, 'x["names"][2] is not a string')

        x = {
            'names': ['alice', 'bob'],
            'city': 5
        }
        error = check_dict(keys)('x', x)
        self.assertEqual(error, 'x["city"] is not a string')

    def test_encapsulation(self):
        # There might be situations where we want deep
        # validation, but the error message should be customized.
        # This is an example.
        def check_person(val):
            error = check_dict([
                ['name', check_string],
                ['age', check_int],
            ])('_', val)
            if error:
                return 'This is not a valid person'

        person = {'name': 'King Lear', 'age': 42}
        self.assertEqual(check_person(person), None)

        person = 'misconfigured data'
        self.assertEqual(check_person(person), 'This is not a valid person')

class DeactivatedRealmTest(AuthedTestCase):
    def test_send_deactivated_realm(self):
        """
        rest_dispatch rejects requests in a deactivated realm, both /json and api

        """
        realm = get_realm("zulip.com")
        do_deactivate_realm(get_realm("zulip.com"))

        result = self.client.post("/json/messages", {"type": "private",
                                                     "content": "Test message",
                                                     "client": "test suite",
                                                     "to": "othello@zulip.com"})
        self.assert_json_error_contains(result, "Not logged in", status_code=401)

        # Even if a logged-in session was leaked, it still wouldn't work
        realm.deactivated = False
        realm.save()
        self.login("hamlet@zulip.com")
        realm.deactivated = True
        realm.save()

        result = self.client.post("/json/messages", {"type": "private",
                                                     "content": "Test message",
                                                     "client": "test suite",
                                                     "to": "othello@zulip.com"})
        self.assert_json_error_contains(result, "has been deactivated", status_code=400)

        result = self.client.post("/api/v1/messages", {"type": "private",
                                                       "content": "Test message",
                                                       "client": "test suite",
                                                       "to": "othello@zulip.com"},
                                  **self.api_auth("hamlet@zulip.com"))
        self.assert_json_error_contains(result, "has been deactivated", status_code=401)

    def test_fetch_api_key_deactivated_realm(self):
        """
        authenticated_json_view views fail in a deactivated realm

        """
        realm = get_realm("zulip.com")
        email = "hamlet@zulip.com"
        test_password = "abcd1234"
        user_profile = get_user_profile_by_email(email)
        user_profile.set_password(test_password)

        self.login(email)
        realm.deactivated = True
        realm.save()
        result = self.client.post("/json/fetch_api_key", {"password": test_password})
        self.assert_json_error_contains(result, "has been deactivated", status_code=400)

    def test_login_deactivated_realm(self):
        """
        logging in fails in a deactivated realm

        """
        do_deactivate_realm(get_realm("zulip.com"))
        result = self.login("hamlet@zulip.com")
        self.assertIn("has been deactivated", result.content.replace("\n", " "))

    def test_webhook_deactivated_realm(self):
        """
        Using a webhook while in a deactivated realm fails

        """
        do_deactivate_realm(get_realm("zulip.com"))
        email = "hamlet@zulip.com"
        api_key = self.get_api_key(email)
        url = "/api/v1/external/jira?api_key=%s&stream=jira_custom" % (api_key,)
        data = self.fixture_data('jira', "created")
        result = self.client.post(url, data,
                                  content_type="application/json")
        self.assert_json_error_contains(result, "has been deactivated", status_code=400)

class LoginRequiredTest(AuthedTestCase):
    def test_login_required(self):
        """
        Verifies the zulip_login_required decorator blocks deactivated users.
        """
        email = "hamlet@zulip.com"
        user_profile = get_user_profile_by_email(email)

        # Verify fails if logged-out
        result = self.client.get('/accounts/accept_terms/')
        self.assertEqual(result.status_code, 302)

        # Verify succeeds once logged-in
        self.login(email)
        result = self.client.get('/accounts/accept_terms/')
        self.assertIn("I agree to the", result.content)

        # Verify fails if user deactivated (with session still valid)
        user_profile.is_active = False
        user_profile.save()
        result = self.client.get('/accounts/accept_terms/')
        self.assertEqual(result.status_code, 302)

        # Verify succeeds if user reactivated
        do_reactivate_user(user_profile)
        self.login(email)
        result = self.client.get('/accounts/accept_terms/')
        self.assertIn("I agree to the", result.content)

        # Verify fails if realm deactivated
        user_profile.realm.deactivated = True
        user_profile.realm.save()
        result = self.client.get('/accounts/accept_terms/')
        self.assertEqual(result.status_code, 302)

class InactiveUserTest(AuthedTestCase):
    def test_send_deactivated_user(self):
        """
        rest_dispatch rejects requests from deactivated users, both /json and api

        """
        email = "hamlet@zulip.com"
        user_profile = get_user_profile_by_email(email)
        self.login(email)
        do_deactivate_user(user_profile)

        result = self.client.post("/json/messages", {"type": "private",
                                                     "content": "Test message",
                                                     "client": "test suite",
                                                     "to": "othello@zulip.com"})
        self.assert_json_error_contains(result, "Not logged in", status_code=401)

        # Even if a logged-in session was leaked, it still wouldn't work
        do_reactivate_user(user_profile)
        self.login(email)
        user_profile.is_active = False
        user_profile.save()

        result = self.client.post("/json/messages", {"type": "private",
                                                     "content": "Test message",
                                                     "client": "test suite",
                                                     "to": "othello@zulip.com"})
        self.assert_json_error_contains(result, "Account not active", status_code=400)

        result = self.client.post("/api/v1/messages", {"type": "private",
                                                       "content": "Test message",
                                                       "client": "test suite",
                                                       "to": "othello@zulip.com"},
                                  **self.api_auth("hamlet@zulip.com"))
        self.assert_json_error_contains(result, "Account not active", status_code=401)

    def test_fetch_api_key_deactivated_user(self):
        """
        authenticated_json_view views fail with a deactivated user

        """
        email = "hamlet@zulip.com"
        user_profile = get_user_profile_by_email(email)
        test_password = "abcd1234"
        user_profile.set_password(test_password)

        self.login(email)
        user_profile.is_active = False
        user_profile.save()
        result = self.client.post("/json/fetch_api_key", {"password": test_password})
        self.assert_json_error_contains(result, "Account not active", status_code=400)

    def test_login_deactivated_user(self):
        """
        logging in fails with an inactive user

        """
        email = "hamlet@zulip.com"
        user_profile = get_user_profile_by_email(email)
        do_deactivate_user(user_profile)

        result = self.login("hamlet@zulip.com")
        self.assertIn("Please enter a correct email and password", result.content.replace("\n", " "))

    def test_webhook_deactivated_user(self):
        """
        Deactivated users can't use webhooks

        """
        email = "hamlet@zulip.com"
        user_profile = get_user_profile_by_email(email)
        do_deactivate_user(user_profile)

        api_key = self.get_api_key(email)
        url = "/api/v1/external/jira?api_key=%s&stream=jira_custom" % (api_key,)
        data = self.fixture_data('jira', "created")
        result = self.client.post(url, data,
                                  content_type="application/json")
        self.assert_json_error_contains(result, "Account not active", status_code=400)


class TestValidateApiKey(AuthedTestCase):
    def setUp(self):
        self.webhook_bot = get_user_profile_by_email('webhook-bot@zulip.com')
        self.default_bot = get_user_profile_by_email('hamlet@zulip.com')

    def test_validate_api_key_if_profile_does_not_exist(self):
        with self.assertRaises(JsonableError):
            validate_api_key('email@doesnotexist.com', 'api_key')

    def test_validate_api_key_if_api_key_does_not_match_profile_api_key(self):
        with self.assertRaises(JsonableError):
            validate_api_key(self.webhook_bot.email, 'not_32_length')

        with self.assertRaises(JsonableError):
            validate_api_key(self.webhook_bot.email, self.default_bot.api_key)

    def test_validate_api_key_if_profile_is_not_active(self):
        self._change_is_active_field(self.default_bot, False)
        with self.assertRaises(JsonableError):
            validate_api_key(self.default_bot.email, self.default_bot.api_key)
        self._change_is_active_field(self.default_bot, True)

    def test_validate_api_key_if_profile_is_incoming_webhook_and_is_webhook_is_unset(self):
        with self.assertRaises(JsonableError):
            validate_api_key(self.webhook_bot.email, self.webhook_bot.api_key)

    def test_validate_api_key_if_profile_is_incoming_webhook_and_is_webhook_is_set(self):
        profile = validate_api_key(self.webhook_bot.email, self.webhook_bot.api_key, is_webhook=True)
        self.assertEqual(profile.pk, self.webhook_bot.pk)

    def _change_is_active_field(self, profile, value):
        profile.is_active = value
        profile.save()


class TestAuthenticatedJsonPostViewDecorator(AuthedTestCase):
    def test_authenticated_json_post_view_if_everything_is_correct(self):
        user_email = 'hamlet@zulip.com'
        self._login(user_email)
        response = self._do_test(user_email)
        self.assertEqual(response.status_code, 200)

    def test_authenticated_json_post_view_if_user_is_incoming_webhook(self):
        user_email = 'webhook-bot@zulip.com'
        self._login(user_email, password="test")  # we set a password because user is a bot
        self.assert_json_error_contains(self._do_test(user_email), "Webhook bots can only access webhooks")

    def test_authenticated_json_post_view_if_user_is_not_active(self):
        user_email = 'hamlet@zulip.com'
        user_profile = get_user_profile_by_email(user_email)
        self._login(user_email, password="test")
        # we deactivate user manually because do_deactivate_user removes user session
        user_profile.is_active = False
        user_profile.save()
        self.assert_json_error_contains(self._do_test(user_email), "Account not active")
        do_reactivate_user(user_profile)

    def test_authenticated_json_post_view_if_user_realm_is_deactivated(self):
        user_email = 'hamlet@zulip.com'
        user_profile = get_user_profile_by_email(user_email)
        self._login(user_email)
        # we deactivate user's realm manually because do_deactivate_user removes user session
        user_profile.realm.deactivated = True
        user_profile.realm.save()
        self.assert_json_error_contains(self._do_test(user_email), "Realm for account has been deactivated")
        do_reactivate_realm(user_profile.realm)

    def _do_test(self, user_email):
        data = {"status": '"started"'}
        return self.client.post(r'/json/tutorial_status', data)

    def _login(self, user_email, password=None):
        if password:
            user_profile = get_user_profile_by_email(user_email)
            user_profile.set_password(password)
            user_profile.save()
        self.login(user_email, password)
