# -*- coding: utf-8 -*-

import re
import mock
from typing import Dict, Any, Set

from django.conf import settings

import zerver.lib.openapi as openapi
from zerver.lib.test_classes import ZulipTestCase
from zerver.lib.openapi import (
    get_openapi_fixture, get_openapi_parameters,
    validate_against_openapi_schema, to_python_type, SchemaError, openapi_spec
)
from zerver.lib.request import arguments_map

TEST_ENDPOINT = '/messages/{message_id}'
TEST_METHOD = 'patch'
TEST_RESPONSE_BAD_REQ = '400'
TEST_RESPONSE_SUCCESS = '200'


class OpenAPIToolsTest(ZulipTestCase):
    """Make sure that the tools we use to handle our OpenAPI specification
    (located in zerver/lib/openapi.py) work as expected.

    These tools are mostly dedicated to fetching parts of the -already parsed-
    specification, and comparing them to objects returned by our REST API.
    """
    def test_get_openapi_fixture(self) -> None:
        actual = get_openapi_fixture(TEST_ENDPOINT, TEST_METHOD,
                                     TEST_RESPONSE_BAD_REQ)
        expected = {
            'code': 'BAD_REQUEST',
            'msg': 'You don\'t have permission to edit this message',
            'result': 'error'
        }
        self.assertEqual(actual, expected)

    def test_get_openapi_parameters(self) -> None:
        actual = get_openapi_parameters(TEST_ENDPOINT, TEST_METHOD)
        expected_item = {
            'name': 'message_id',
            'in': 'path',
            'description':
                'The ID of the message that you wish to edit/update.',
            'example': 42,
            'required': True,
            'schema': {'type': 'integer'}
        }
        assert(expected_item in actual)

    def test_validate_against_openapi_schema(self) -> None:
        with self.assertRaises(SchemaError,
                               msg=('Extraneous key "foo" in '
                                    'the response\'scontent')):
            bad_content = {
                'msg': '',
                'result': 'success',
                'foo': 'bar'
            }  # type: Dict[str, Any]
            validate_against_openapi_schema(bad_content,
                                            TEST_ENDPOINT,
                                            TEST_METHOD,
                                            TEST_RESPONSE_SUCCESS)

        with self.assertRaises(SchemaError,
                               msg=("Expected type <class 'str'> for key "
                                    "\"msg\", but actually got "
                                    "<class 'int'>")):
            bad_content = {
                'msg': 42,
                'result': 'success',
            }
            validate_against_openapi_schema(bad_content,
                                            TEST_ENDPOINT,
                                            TEST_METHOD,
                                            TEST_RESPONSE_SUCCESS)

        with self.assertRaises(SchemaError,
                               msg='Expected to find the "msg" required key'):
            bad_content = {
                'result': 'success',
            }
            validate_against_openapi_schema(bad_content,
                                            TEST_ENDPOINT,
                                            TEST_METHOD,
                                            TEST_RESPONSE_SUCCESS)

        # No exceptions should be raised here.
        good_content = {
            'msg': '',
            'result': 'success',
        }
        validate_against_openapi_schema(good_content,
                                        TEST_ENDPOINT,
                                        TEST_METHOD,
                                        TEST_RESPONSE_SUCCESS)

        # Overwrite the exception list with a mocked one
        openapi.EXCLUDE_PROPERTIES = {
            TEST_ENDPOINT: {
                TEST_METHOD: {
                    TEST_RESPONSE_SUCCESS: ['foo']
                }
            }
        }
        good_content = {
            'msg': '',
            'result': 'success',
            'foo': 'bar'
        }
        validate_against_openapi_schema(good_content,
                                        TEST_ENDPOINT,
                                        TEST_METHOD,
                                        TEST_RESPONSE_SUCCESS)

    def test_to_python_type(self) -> None:
        TYPES = {
            'string': str,
            'number': float,
            'integer': int,
            'boolean': bool,
            'array': list,
            'object': dict
        }

        for oa_type, py_type in TYPES.items():
            self.assertEqual(to_python_type(oa_type), py_type)

    def test_live_reload(self) -> None:
        # Force the reload by making the last update date < the file's last
        # modified date
        openapi_spec.last_update = 0
        get_openapi_fixture(TEST_ENDPOINT, TEST_METHOD)

        # Check that the file has been reloaded by verifying that the last
        # update date isn't zero anymore
        self.assertNotEqual(openapi_spec.last_update, 0)

        # Now verify calling it again doesn't call reload
        with mock.patch('zerver.lib.openapi.openapi_spec.reload') as mock_reload:
            get_openapi_fixture(TEST_ENDPOINT, TEST_METHOD)
            self.assertFalse(mock_reload.called)

class OpenAPIArgumentsTest(ZulipTestCase):
    def test_openapi_arguments(self) -> None:
        # Verifies that every REQ-defined argument appears in our API
        # documentation for the target endpoint where possible.

        # These should have docs added
        PENDING_ENDPOINTS = set([
            '/users/me/avatar',
            '/user_uploads',
            '/settings/display',
            '/settings/notifications',
            '/users/me/profile_data',
            '/user_groups',
            '/user_groups/create',
            '/users/me/pointer',
            '/users/me/presence',
            '/users/me',
            '/bot_storage',
            '/users/me/api_key/regenerate',
            '/default_streams',
            '/default_stream_groups/create',
            '/users/me/alert_words',
            '/users/me/status',
            '/users/me/subscriptions',
            '/messages/matches_narrow',
            '/settings',
            '/submessage',
            '/attachments',
            '/calls/create',
            '/export/realm',
            '/mark_all_as_read',
            '/zcommand',
            '/realm',
            '/realm/deactivate',
            '/realm/domains',
            '/realm/emoji',
            '/realm/filters',
            '/realm/icon',
            '/realm/logo',
            '/realm/presence',
            '/realm/profile_fields',
            '/queue_id',
            '/invites',
            '/invites/multiuse',
            '/bots',
            # Mobile-app only endpoints
            '/users/me/android_gcm_reg_id',
            '/users/me/apns_device_token',
            # Regex based urls
            '/realm/domains/<domain>',
            '/realm/filters/<filter_id>',
            '/realm/profile_fields/<field_id>',
            '/users/<user_id>/reactivate',
            '/users/<user_id>',
            '/bots/<bot_id>/api_key/regenerate',
            '/bots/<bot_id>',
            '/invites/<prereg_id>',
            '/invites/<prereg_id>/resend',
            '/invites/multiuse/<invite_id>',
            '/messages/<message_id>',
            '/messages/<message_id>',
            '/messages/<message_id>',
            '/messages/<message_id>/history',
            '/users/me/subscriptions/<stream_id>',
            '/messages/<message_id>/reactions',
            '/messages/<message_id>/reactions',
            '/messages/<message_id>/emoji_reactions/<emoji_name>',
            '/messages/<message_id>/emoji_reactions/<emoji_name>',
            '/attachments/<attachment_id>',
            '/user_groups/<user_group_id>',
            '/user_groups/<user_group_id>',
            '/user_groups/<user_group_id>/members',
            '/users/me/<stream_id>/topics',
            '/streams/<stream_id>/members',
            '/streams/<stream_id>',
            '/streams/<stream_id>',
            '/streams/<stream_id>/delete_topic',
            '/default_stream_groups/<group_id>',
            '/default_stream_groups/<group_id>',
            '/default_stream_groups/<group_id>/streams',
            # Regex with an unnamed capturing group.
            '/users/(?!me/)(?P<email>[^/]*)/presence',
        ])

        # These endpoints have a mismatch between the documentation
        # and the actual API.  There are situations where we may want
        # to have undocumented parameters for e.g. backwards
        # compatibility, which could be the situation for some of
        # these, in which case we may want a more clever exclude
        # system.  This list can serve as a TODO list for such an
        # investigation.
        BUGGY_DOCUMENTATION_ENDPOINTS = set([
            '/events',
            '/users/me/subscriptions/muted_topics',
        ])

        # First, we import the fancy-Django version of zproject/urls.py
        urlconf = __import__(getattr(settings, "ROOT_URLCONF"), {}, {}, [''])
        # Import some view modules not already imported in urls.py, we use
        # this round about manner because of the linters complaining of an
        # unused import (which is correct, but we do this for triggering the
        # has_request_variables decorator).
        __import__('zerver.views.typing')
        __import__('zerver.views.events_register')
        __import__('zerver.views.realm_emoji')

        # We loop through all the API patterns, looking in particular
        # those using the rest_dispatch decorator; we then parse its
        # mapping of (HTTP_METHOD -> FUNCTION).
        for p in urlconf.v1_api_and_json_patterns:
            if p.lookup_str != 'zerver.lib.rest.rest_dispatch':
                continue
            for method, value in p.default_args.items():
                if isinstance(value, str):
                    function = value
                    tags = set()  # type: Set[str]
                else:
                    function, tags = value
                # Our accounting logic in the `has_request_variables()`
                # code means we have the list of all arguments
                # accepted by every view function in arguments_map.
                #
                # TODO: Probably with a bit more work, we could get
                # the types, too; `check_int` -> `int`, etc., and
                # verify those too!
                accepted_arguments = set(arguments_map[function])

                # The purpose of this block is to match our URL
                # pattern regular expressions to the corresponding
                # configuration in OpenAPI.  The means matching
                #
                # /messages/{message_id} <-> r'^messages/(?P<message_id>[0-9]+)$'
                # /events <-> r'^events$'
                regex_pattern = p.regex.pattern
                self.assertTrue(regex_pattern.startswith("^"))
                self.assertTrue(regex_pattern.endswith("$"))
                url_pattern = '/' + regex_pattern[1:][:-1]
                # Deal with the conversion of named capturing groups:
                # Two possible ways to denote variables in urls exist.
                # {var_name} and <var_name>. So we need to consider both.
                url_patterns = [re.sub(r"\(\?P<(\w+)>[^/]+\)", r"<\1>", url_pattern),
                                re.sub(r"\(\?P<(\w+)>[^/]+\)", r"{\1}", url_pattern)]

                if any([url_patterns[0] in PENDING_ENDPOINTS,
                        url_patterns[1] in PENDING_ENDPOINTS]):
                    continue
                if "intentionally_undocumented" in tags:
                    error = AssertionError("We found some OpenAPI \
documentation for %s %s, so maybe we shouldn't mark it as intentionally \
undocumented in the urls." % (method, url_patterns[0] + " or " + url_patterns[1]))

                    try:
                        get_openapi_parameters(url_patterns[0], method)
                        raise error  # nocoverage
                    except KeyError:
                        pass

                    try:
                        get_openapi_parameters(url_patterns[1], method)
                        raise error  # nocoverage
                    except KeyError:
                        pass

                    continue  # nocoverage # although, this *is* covered.

                try:
                    openapi_parameters = get_openapi_parameters(url_patterns[0], method)
                except Exception:  # nocoverage
                    try:
                        openapi_parameters = get_openapi_parameters(url_patterns[1], method)
                    except Exception:  # nocoverage
                        raise AssertionError("Could not find OpenAPI docs for %s %s" %
                                             (method, url_patterns[0] + " or " + url_patterns[1]))

                # We now have everything we need to understand the
                # function as defined in our urls.py
                #
                # * method is the HTTP method, e.g. GET, POST, or PATCH
                #
                # * p.regex.pattern is the URL pattern; might require
                #   some processing to match with OpenAPI rules
                #
                # * accepted_arguments_list is the full set of arguments
                #   this method accepts.
                #
                # * The documented parameters for the endpoint as recorded in our
                #   OpenAPI data in zerver/openapi/zulip.yaml.
                #
                # We now compare these to confirm that the documented
                # argument list matches what actually appears in the
                # codebase.

                openapi_parameter_names = set(
                    [parameter['name'] for parameter in openapi_parameters]
                )

                if len(openapi_parameter_names - accepted_arguments) > 0:
                    print("Undocumented parameters for",
                          url_patterns[0] + " or " + url_patterns[1],
                          method, function)
                    print(" +", openapi_parameter_names)
                    print(" -", accepted_arguments)
                    assert(any([url_patterns[0] in BUGGY_DOCUMENTATION_ENDPOINTS,
                                url_patterns[1] in BUGGY_DOCUMENTATION_ENDPOINTS]))
                elif len(accepted_arguments - openapi_parameter_names) > 0:
                    print("Documented invalid parameters for",
                          url_patterns[0] + " or " + url_patterns[1],
                          method, function)
                    print(" -", openapi_parameter_names)
                    print(" +", accepted_arguments)
                    assert(any([url_patterns[0] in BUGGY_DOCUMENTATION_ENDPOINTS,
                                url_patterns[1] in BUGGY_DOCUMENTATION_ENDPOINTS]))
                else:
                    self.assertEqual(openapi_parameter_names, accepted_arguments)
