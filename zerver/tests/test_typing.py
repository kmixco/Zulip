# -*- coding: utf-8 -*-
from __future__ import absolute_import

import ujson
from typing import Any, Dict, List
from six import string_types

from zerver.models import get_user_profile_by_email

from zerver.lib.test_helpers import ZulipTestCase, tornado_redirected_to_list, get_display_recipient

class TypingNotificationEndToEndTest(ZulipTestCase):
    def test_post_result(self):
        # type: () -> None
        """
        Sending typing notification results in success response
        """
        sender = 'hamlet@zulip.com'
        recipient = 'othello@zulip.com'
        result = self.client_post('/api/v1/typing', {'to': recipient, 'op': 'start'},
                                  **self.api_auth(sender))
        self.assert_json_success(result)

    def test_single_recipient(self):
        # type: () -> None
        """
        Single recipient can retrieve typing event from queue
        """
        sender = 'hamlet@zulip.com'
        recipient = 'othello@zulip.com'
        register_result = self.client_post('/api/v1/register', {'event_types': ['typing']},
                                           **self.api_auth(recipient))
        self.assert_json_success(register_result)

        typing_result = self.client_post('/api/v1/typing', {'to': recipient, 'op': 'start'},
                                         **self.api_auth(sender))
        self.assert_json_success(typing_result)

        event = self.client_post('/api/v1/events', {'queue_id': register_result.queue_id},
                                  **self.api_auth(sender))
        self.assert_json_success(event)

        event_recipient_emails = set(user['email'] for user in event['recipients'])

        self.assertTrue(event['sender'] == get_user_profile_by_email(sender))
        self.assertTrue(event_recipient_emails == expected_recipients)
        self.assertTrue(event['type'] == 'typing')
        self.assertTrue(event['op'] == 'start')

    def test_multiple_recipients(self):
        # type: () -> None
        """
        All recipients can retrieve typing event
        """
        sender = 'hamlet@zulip.com'
        recipient = ['othello@zulip.com', 'cordelia@zulip.com']
        expected_recipients = set(recipient) | set([sender])

        recipient_queues = []
        for user in recipient:
            result = self.client_post('/api/v1/register', {'event_types': ['typing']},
                                      **self.api_auth(user))
            self.assert_json_success(result)
            recipient_queues.push((user, result.queue_id))

        typing_result = self.client_post('/api/v1/typing', {'to': recipient, 'op': 'start'},
                                         **self.api_auth(sender))
        self.assert_json_success(typing_result)

        for user, queue_id in recipient_queues:
            event = self.client_post('/api/v1/events', {'queue_id': queue_id},
                                     **self.api_auth(user))
            self.assert_json_success(event)

            event_recipient_emails = set(user['email'] for user in event['recipients'])

            self.assertTrue(event['sender'] == get_user_profile_by_email(sender))
            self.assertTrue(event_recipient_emails == expected_recipients)
            self.assertTrue(event['type'] == 'typing')
            self.assertTrue(event['op'] == 'start')

class TypingNotificationOperatorTest(ZulipTestCase):
    def test_missing_parameter(self):
        # type: () -> None
        """
        Sending typing notification without op parameter fails
        """
        sender = 'hamlet@zulip.com'
        recipient = 'othello@zulip.com'
        result = self.client_post('/api/v1/typing', {'to': recipient},
                                  **self.api_auth(sender))
        self.assert_json_error(result, 'Missing \'op\' argument')

    def test_invalid_parameter(self):
        # type: () -> None
        """
        Sending typing notification with invalid value for op parameter fails
        """
        sender = 'hamlet@zulip.com'
        recipient = 'othello@zulip.com'
        result = self.client_post('/api/v1/typing', {'to': recipient, 'op': 'foo'},
                                  **self.api_auth(sender))
        self.assert_json_error(result, 'Invalid \'op\' value (should be start or stop)')

class TypingNotificationRecipientsTest(ZulipTestCase):
    def test_missing_recipient(self):
        # type: () -> None
        """
        Sending typing notification without recipient fails
        """
        sender = 'hamlet@zulip.com'
        result = self.client_post('/api/v1/typing', {'op': 'start'},
                                  **self.api_auth(sender))
        self.assert_json_error(result, 'Missing parameter: \'to\' (recipient)')

    def test_invalid_recipient(self):
        # type: () -> None
        """
        Sending typing notification to invalid recipient fails
        """
        sender = 'hamlet@zulip.com'
        invalid = 'invalid email'
        result = self.client_post('/api/v1/typing', {'op': 'start', 'to': invalid},
                                  **self.api_auth(sender))
        self.assert_json_error(result, 'Invalid email \'' + invalid + '\'')

    def test_single_recipient(self):
        # type: () -> None
        """
        Sending typing notification to a single recipient is successful
        """
        sender = 'hamlet@zulip.com'
        recipient = 'othello@zulip.com'
        expected_recipients = set([sender, recipient])

        events = [] # type: List[Dict[str, Any]]
        with tornado_redirected_to_list(events):
            result = self.client_post('/api/v1/typing', {'to': recipient,
                                                         'op': 'start'},
                                      **self.api_auth(sender))
        self.assert_json_success(result)
        self.assertTrue(len(events) == 1)

        event = events[0]['event']
        event_recipient_emails = set(user['email'] for user in event['recipients'])

        self.assertTrue(event['sender'] == get_user_profile_by_email(sender))
        self.assertTrue(event_recipient_emails == expected_recipients)
        self.assertTrue(event['type'] == 'typing')
        self.assertTrue(event['op'] == 'start')

    def test_multiple_recipients(self):
        # type: () -> None
        """
        Sending typing notification to a single recipient is successful
        """
        sender = 'hamlet@zulip.com'
        recipient = ['othello@zulip.com', 'cordelia@zulip.com']
        expected_recipients = set(recipient) | set([sender])

        events = [] # type: List[Dict[str, Any]]
        with tornado_redirected_to_list(events):
            result = self.client_post('/api/v1/typing', {'to': ujson.dumps(recipient),
                                                         'op': 'start'},
                                      **self.api_auth(sender))
        self.assert_json_success(result)
        self.assertTrue(len(events) == 1)

        event = events[0]['event']
        event_recipient_emails = set(user['email'] for user in event['recipients'])

        self.assertTrue(event['sender'] == get_user_profile_by_email(sender))
        self.assertTrue(event_recipient_emails == expected_recipients)
        self.assertTrue(event['type'] == 'typing')
        self.assertTrue(event['op'] == 'start')

class TypingStartedNotificationTest(ZulipTestCase):
    def test_send_notification_to_self_event(self):
        # type: () -> None
        """
        Sending typing notification to yourself
        is successful.
        """
        email = 'hamlet@zulip.com'

        events = [] # type: List[Dict[str, Any]]
        with tornado_redirected_to_list(events):
            result = self.client_post('/api/v1/typing', {'to': email,
                                                         'op': 'start'},
                                      **self.api_auth(email))
        self.assert_json_success(result)
        self.assertTrue(len(events) == 1)

        event = events[0]['event']
        event_recipient_emails = set(user['email'] for user in event['recipients'])

        self.assertTrue(event['sender'] == get_user_profile_by_email(email))
        self.assertTrue(event_recipient_emails == set([email]))
        self.assertTrue(event['type'] == 'typing')
        self.assertTrue(event['op'] == 'start')

    def test_send_notification_to_another_user_event(self):
        # type: () -> None
        """
        Sending typing notification to another user
        is successful.
        """
        sender = 'hamlet@zulip.com'
        recipient = 'othello@zulip.com'
        expected_recipients = set([sender, recipient])
        events = [] # type: List[Dict[str, Any]]
        with tornado_redirected_to_list(events):
            result = self.client_post('/api/v1/typing', {'to': recipient,
                                                         'op': 'start'},
                                      **self.api_auth(sender))
        self.assert_json_success(result)
        self.assertTrue(len(events) == 1)

        event = events[0]['event']
        event_recipient_emails = set(user['email'] for user in event['recipients'])
        self.assertTrue(event['sender'] == get_user_profile_by_email(sender))
        self.assertTrue(event_recipient_emails == expected_recipients)
        self.assertTrue(event['type'] == 'typing')
        self.assertTrue(event['op'] == 'start')

class StoppedTypingNotificationTest(ZulipTestCase):
    def test_send_notification_to_self_event(self):
        # type: () -> None
        """
        Sending stopped typing notification to yourself
        is successful.
        """
        email = 'hamlet@zulip.com'

        events = [] # type: List[Dict[str, Any]]
        with tornado_redirected_to_list(events):
            result = self.client_post('/api/v1/typing', {'to': email,
                                                         'op': 'stop'},
                                      **self.api_auth(email))
        self.assert_json_success(result)
        self.assertTrue(len(events) == 1)

        event = events[0]['event']
        event_recipient_emails = set(user['email'] for user in event['recipients'])
        self.assertTrue(event['sender'] == get_user_profile_by_email(email))
        self.assertTrue(event_recipient_emails == set([email]))
        self.assertTrue(event['type'] == 'typing')
        self.assertTrue(event['op'] == 'stop')


    def test_send_notification_to_another_user_event(self):
        # type: () -> None
        """
        Sending stopped typing notification to another user
        is successful.
        """
        sender = 'hamlet@zulip.com'
        recipient = 'othello@zulip.com'
        expected_recipients = set([sender, recipient])
        events = [] # type: List[Dict[str, Any]]
        with tornado_redirected_to_list(events):
            result = self.client_post('/api/v1/typing', {'to': recipient,
                                                         'op': 'stop'},
                                      **self.api_auth(sender))
        self.assert_json_success(result)
        self.assertTrue(len(events) == 1)

        event = events[0]['event']
        event_recipient_emails = set(user['email'] for user in event['recipients'])
        self.assertTrue(event['sender'] == get_user_profile_by_email(sender))
        self.assertTrue(event_recipient_emails == expected_recipients)
        self.assertTrue(event['type'] == 'typing')
        self.assertTrue(event['op'] == 'stop')
