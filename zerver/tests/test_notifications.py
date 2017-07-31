# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function

import random
import re
import ujson

from django.conf import settings
from django.core import mail
from django.http import HttpResponse
from django.test import override_settings
from email.utils import formataddr, parseaddr
from mock import patch, MagicMock
from six.moves import range
from typing import Any, Dict, List, Text

from zerver.lib.notifications import handle_missedmessage_emails
from zerver.lib.actions import render_incoming_message, do_update_message
from zerver.lib.message import access_message
from zerver.lib.test_classes import ZulipTestCase
from zerver.lib.send_email import FromAddress
from zerver.models import (
    Recipient,
    UserMessage,
    UserProfile,
    Realm,
)
from zerver.lib.test_helpers import get_test_image_file, find_key_by_email

class TestMissedMessages(ZulipTestCase):
    def normalize_string(self, s):
        # type: (Text) -> Text
        s = s.strip()
        return re.sub(r'\s+', ' ', s)

    def _get_tokens(self):
        # type: () -> List[str]
        return [str(random.getrandbits(32)) for _ in range(30)]

    def _test_cases(self, tokens, msg_id, body, subject, reply_to_name, send_as_user, verify_html_body=False):
        # type: (List[str], int, str, Text, str, bool, bool) -> None
        othello = self.example_user('othello')
        hamlet = self.example_user('hamlet')
        handle_missedmessage_emails(hamlet.id, [{'message_id': msg_id}])
        if settings.EMAIL_GATEWAY_PATTERN != "":
            reply_to_addresses = [settings.EMAIL_GATEWAY_PATTERN % (u'mm' + t) for t in tokens]
        else:
            reply_to_addresses = ["noreply@zulip.example.com"]
        msg = mail.outbox[0]
        from_email = formataddr(("Zulip missed messages", FromAddress.NOREPLY))
        self.assertEqual(len(mail.outbox), 1)
        if send_as_user:
            from_email = '"%s" <%s>' % (othello.full_name, othello.email)
        self.assertEqual(msg.from_email, from_email)
        self.assertEqual(msg.subject, subject)
        self.assertEqual(len(msg.reply_to), 1)
        parsed_reply_to = parseaddr(msg.reply_to[0])
        self.assertEqual(parsed_reply_to[0], reply_to_name)
        self.assertIn(parsed_reply_to[1], reply_to_addresses)
        if verify_html_body:
            self.assertIn(body, self.normalize_string(msg.alternatives[0][0]))
        else:
            self.assertIn(body, self.normalize_string(msg.body))

    @patch('zerver.lib.email_mirror.generate_random_token')
    def _extra_context_in_missed_stream_messages_mention(self, send_as_user, mock_random_token):
        # type: (bool, MagicMock) -> None
        tokens = self._get_tokens()
        mock_random_token.side_effect = tokens

        for i in range(0, 11):
            self.send_message(self.example_email('othello'), "Denmark", Recipient.STREAM, str(i))
        self.send_message(self.example_email('othello'), "Denmark", Recipient.STREAM, '11', subject='test2')
        msg_id = self.send_message(self.example_email('othello'), "denmark", Recipient.STREAM, '@**King Hamlet**')
        body = 'Denmark > test Othello, the Moor of Venice 1 2 3 4 5 6 7 8 9 10 @**King Hamlet**'
        subject = 'Othello, the Moor of Venice mentioned you'
        reply_to_name = "#Denmark"
        self._test_cases(tokens, msg_id, body, subject, reply_to_name, send_as_user)

    @patch('zerver.lib.email_mirror.generate_random_token')
    def _extra_context_in_missed_stream_messages_mention_two_senders(self, send_as_user, mock_random_token):
        # type: (bool, MagicMock) -> None
        tokens = self._get_tokens()
        mock_random_token.side_effect = tokens

        for i in range(0, 3):
            self.send_message(self.example_email('cordelia'), "Denmark", Recipient.STREAM, str(i))
        msg_id = self.send_message(self.example_email('othello'), "Denmark", Recipient.STREAM, '@**King Hamlet**')
        body = 'Denmark > test Cordelia Lear 0 1 2 Othello, the Moor of Venice @**King Hamlet**'
        subject = 'Othello, the Moor of Venice mentioned you'
        reply_to_name = "#Denmark"
        self._test_cases(tokens, msg_id, body, subject, reply_to_name, send_as_user)

    @patch('zerver.lib.email_mirror.generate_random_token')
    def _extra_context_in_personal_missed_stream_messages(self, send_as_user, mock_random_token):
        # type: (bool, MagicMock) -> None
        tokens = self._get_tokens()
        mock_random_token.side_effect = tokens

        msg_id = self.send_message(self.example_email('othello'), self.example_email('hamlet'),
                                   Recipient.PERSONAL,
                                   'Extremely personal message!')
        body = 'You and Othello, the Moor of Venice Extremely personal message!'
        subject = 'Othello, the Moor of Venice sent you a message'
        reply_to_name = "Othello, the Moor of Venice"
        self._test_cases(tokens, msg_id, body, subject, reply_to_name, send_as_user)

    @patch('zerver.lib.email_mirror.generate_random_token')
    def _reply_to_email_in_personal_missed_stream_messages(self, send_as_user, mock_random_token):
        # type: (bool, MagicMock) -> None
        tokens = self._get_tokens()
        mock_random_token.side_effect = tokens

        msg_id = self.send_message(self.example_email('othello'), self.example_email('hamlet'),
                                   Recipient.PERSONAL,
                                   'Extremely personal message!')
        body = 'Or just reply to this email.'
        subject = 'Othello, the Moor of Venice sent you a message'
        reply_to_name = "Othello, the Moor of Venice"
        self._test_cases(tokens, msg_id, body, subject, reply_to_name, send_as_user)

    @patch('zerver.lib.email_mirror.generate_random_token')
    def _reply_to_email_in_personal_missed_stream_messages_non_ascii_username(self, send_as_user, mock_random_token):
        # type: (bool, MagicMock) -> None
        # email = "newguy@zulip.com"
        # password = "newpassword"

        # result = self.client_post('/accounts/home/', {'email': email})
        # self.assertEqual(result.status_code, 302)
        # self.assertTrue(result["Location"].endswith(
        #     "/accounts/send_confirm/%s" % (email,)))
        # result = self.client_get(result["Location"])
        # self.assert_in_response("Check your email so we can get started.", result)

        # Visit the confirmation link.
        # confirmation_url = self.get_confirmation_url_from_outbox(email)
        # result = self.client_get(confirmation_url)
        # self.assertEqual(result.status_code, 200)

        # self.assert_in_success_response(["You're almost there."], result)

        # self.register("newguy@zulip.com", "newpassword")
        self.client_post('/accounts/home/',
                         {'email': 'newguy@zulip.com'})
        self.client_post('/accounts/register/',
                         {'password': 'newpassword',
                          'realm_name': 'Zulip Dev',
                          'realm_subdomain': 'zuliptest',
                          'key': find_key_by_email('newguy@zulip.com'),
                          'realm_org_type': Realm.COMMUNITY,
                          'terms': True,
                          'full_name': u'Ñew Guy',
                          'from_confirmation': ''})
        mail.outbox.pop()

        tokens = self._get_tokens()
        mock_random_token.side_effect = tokens

        msg_id = self.send_message('newguy@zulip.com', self.example_email('hamlet'),
                                   Recipient.PERSONAL,
                                   'Extremely personal message!')
        body = 'Or just reply to this email.'
        subject = u'Ñew Guy sent you a message'
        # We want the reply-to email address 'reply_to_name <newguy@zulip.com>'
        # to be MIME word-encoded. This is the encoding for 'Ñew Guy' in utf-8.
        reply_to_name = '=?utf-8?q?=C3=91ew_Guy?='
        self._test_cases(tokens, msg_id, body, subject, reply_to_name, send_as_user)

    @patch('zerver.lib.email_mirror.generate_random_token')
    def _reply_warning_in_personal_missed_stream_messages(self, send_as_user, mock_random_token):
        # type: (bool, MagicMock) -> None
        tokens = self._get_tokens()
        mock_random_token.side_effect = tokens

        msg_id = self.send_message(self.example_email('othello'), self.example_email('hamlet'),
                                   Recipient.PERSONAL,
                                   'Extremely personal message!')
        body = 'Please do not reply to this automated message.'
        subject = 'Othello, the Moor of Venice sent you a message'
        reply_to_name = ""
        self._test_cases(tokens, msg_id, body, subject, reply_to_name, send_as_user)

    @patch('zerver.lib.email_mirror.generate_random_token')
    def _extra_context_in_huddle_missed_stream_messages_two_others(self, send_as_user, mock_random_token):
        # type: (bool, MagicMock) -> None
        tokens = self._get_tokens()
        mock_random_token.side_effect = tokens

        msg_id = self.send_message(self.example_email('othello'),
                                   [self.example_email('hamlet'), self.example_email('iago')],
                                   Recipient.HUDDLE,
                                   'Group personal message!')

        body = ('You and Iago, Othello, the Moor of Venice Othello,'
                ' the Moor of Venice Group personal message')
        subject = 'Group PMs with Iago and Othello, the Moor of Venice'
        reply_to_name = "Iago and Othello, the Moor of Venice"
        self._test_cases(tokens, msg_id, body, subject, reply_to_name, send_as_user)

    @patch('zerver.lib.email_mirror.generate_random_token')
    def _extra_context_in_huddle_missed_stream_messages_three_others(self, send_as_user, mock_random_token):
        # type: (bool, MagicMock) -> None
        tokens = self._get_tokens()
        mock_random_token.side_effect = tokens

        msg_id = self.send_message(self.example_email('othello'),
                                   [self.example_email('hamlet'), self.example_email('iago'), self.example_email('cordelia')],
                                   Recipient.HUDDLE,
                                   'Group personal message!')

        body = ('You and Cordelia Lear, Iago, Othello, the Moor of Venice Othello,'
                ' the Moor of Venice Group personal message')
        subject = 'Group PMs with Cordelia Lear, Iago, and Othello, the Moor of Venice'
        reply_to_name = "Cordelia Lear, Iago, and Othello, the Moor of Venice"
        self._test_cases(tokens, msg_id, body, subject, reply_to_name, send_as_user)

    @patch('zerver.lib.email_mirror.generate_random_token')
    def _extra_context_in_huddle_missed_stream_messages_many_others(self, send_as_user, mock_random_token):
        # type: (bool, MagicMock) -> None
        tokens = self._get_tokens()
        mock_random_token.side_effect = tokens

        msg_id = self.send_message(self.example_email('othello'),
                                   [self.example_email('hamlet'),
                                    self.example_email('iago'),
                                    self.example_email('cordelia'),
                                    self.example_email('prospero')],
                                   Recipient.HUDDLE,
                                   'Group personal message!')

        body = ('You and Cordelia Lear, Iago, Othello, the Moor of Venice, Prospero from The Tempest'
                ' Othello, the Moor of Venice Group personal message')
        subject = 'Group PMs with Cordelia Lear, Iago, and 2 others'
        reply_to_name = "Cordelia Lear, Iago, and 2 others"
        self._test_cases(tokens, msg_id, body, subject, reply_to_name, send_as_user)

    @patch('zerver.lib.email_mirror.generate_random_token')
    def _deleted_message_in_missed_stream_messages(self, send_as_user, mock_random_token):
        # type: (bool, MagicMock) -> None
        tokens = self._get_tokens()
        mock_random_token.side_effect = tokens

        msg_id = self.send_message(self.example_email('othello'), "denmark", Recipient.STREAM,
                                   '@**King Hamlet** to be deleted')

        hamlet = self.example_user('hamlet')
        email = self.example_email('othello')
        self.login(email)
        result = self.client_patch('/json/messages/' + str(msg_id),
                                   {'message_id': msg_id, 'content': ' '})
        self.assert_json_success(result)
        handle_missedmessage_emails(hamlet.id, [{'message_id': msg_id}])
        self.assertEqual(len(mail.outbox), 0)

    @patch('zerver.lib.email_mirror.generate_random_token')
    def _deleted_message_in_personal_missed_stream_messages(self, send_as_user, mock_random_token):
        # type: (bool, MagicMock) -> None
        tokens = self._get_tokens()
        mock_random_token.side_effect = tokens

        msg_id = self.send_message(self.example_email('othello'),
                                   self.example_email('hamlet'),
                                   Recipient.PERSONAL,
                                   'Extremely personal message! to be deleted!')

        hamlet = self.example_user('hamlet')
        email = self.example_email('othello')
        self.login(email)
        result = self.client_patch('/json/messages/' + str(msg_id),
                                   {'message_id': msg_id, 'content': ' '})
        self.assert_json_success(result)
        handle_missedmessage_emails(hamlet.id, [{'message_id': msg_id}])
        self.assertEqual(len(mail.outbox), 0)

    @patch('zerver.lib.email_mirror.generate_random_token')
    def _deleted_message_in_huddle_missed_stream_messages(self, send_as_user, mock_random_token):
        # type: (bool, MagicMock) -> None
        tokens = self._get_tokens()
        mock_random_token.side_effect = tokens

        msg_id = self.send_message(self.example_email('othello'),
                                   [self.example_email('hamlet'),
                                    self.example_email('iago')],
                                   Recipient.PERSONAL, 'Group personal message!')

        hamlet = self.example_user('hamlet')
        iago = self.example_user('iago')
        email = self.example_email('othello')
        self.login(email)
        result = self.client_patch('/json/messages/' + str(msg_id),
                                   {'message_id': msg_id, 'content': ' '})
        self.assert_json_success(result)
        handle_missedmessage_emails(hamlet.id, [{'message_id': msg_id}])
        self.assertEqual(len(mail.outbox), 0)
        handle_missedmessage_emails(iago.id, [{'message_id': msg_id}])
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(SEND_MISSED_MESSAGE_EMAILS_AS_USER=True)
    def test_extra_context_in_missed_stream_messages_as_user(self):
        # type: () -> None
        self._extra_context_in_missed_stream_messages_mention(True)

    def test_extra_context_in_missed_stream_messages(self):
        # type: () -> None
        self._extra_context_in_missed_stream_messages_mention(False)

    @override_settings(SEND_MISSED_MESSAGE_EMAILS_AS_USER=True)
    def test_extra_context_in_missed_stream_messages_as_user_two_senders(self):
        # type: () -> None
        self._extra_context_in_missed_stream_messages_mention_two_senders(True)

    def test_extra_context_in_missed_stream_messages_two_senders(self):
        # type: () -> None
        self._extra_context_in_missed_stream_messages_mention_two_senders(False)

    def test_reply_to_email_in_personal_missed_stream_messages(self):
        # type: () -> None
        self._reply_to_email_in_personal_missed_stream_messages(False)

    def test_reply_to_email_in_personal_missed_stream_messages_non_ascii_username(self):
        # type: () -> None
        self._reply_to_email_in_personal_missed_stream_messages_non_ascii_username(False)

    @override_settings(EMAIL_GATEWAY_PATTERN="")
    def test_reply_warning_in_personal_missed_stream_messages(self):
        # type: () -> None
        self._reply_warning_in_personal_missed_stream_messages(False)

    @override_settings(SEND_MISSED_MESSAGE_EMAILS_AS_USER=True)
    def test_extra_context_in_personal_missed_stream_messages_as_user(self):
        # type: () -> None
        self._extra_context_in_personal_missed_stream_messages(True)

    def test_extra_context_in_personal_missed_stream_messages(self):
        # type: () -> None
        self._extra_context_in_personal_missed_stream_messages(False)

    @override_settings(SEND_MISSED_MESSAGE_EMAILS_AS_USER=True)
    def test_extra_context_in_huddle_missed_stream_messages_two_others_as_user(self):
        # type: () -> None
        self._extra_context_in_huddle_missed_stream_messages_two_others(True)

    def test_extra_context_in_huddle_missed_stream_messages_two_others(self):
        # type: () -> None
        self._extra_context_in_huddle_missed_stream_messages_two_others(False)

    @override_settings(SEND_MISSED_MESSAGE_EMAILS_AS_USER=True)
    def test_extra_context_in_huddle_missed_stream_messages_three_others_as_user(self):
        # type: () -> None
        self._extra_context_in_huddle_missed_stream_messages_three_others(True)

    def test_extra_context_in_huddle_missed_stream_messages_three_others(self):
        # type: () -> None
        self._extra_context_in_huddle_missed_stream_messages_three_others(False)

    @override_settings(SEND_MISSED_MESSAGE_EMAILS_AS_USER=True)
    def test_extra_context_in_huddle_missed_stream_messages_many_others_as_user(self):
        # type: () -> None
        self._extra_context_in_huddle_missed_stream_messages_many_others(True)

    def test_extra_context_in_huddle_missed_stream_messages_many_others(self):
        # type: () -> None
        self._extra_context_in_huddle_missed_stream_messages_many_others(False)

    @override_settings(SEND_MISSED_MESSAGE_EMAILS_AS_USER=True)
    def test_deleted_message_in_missed_stream_messages_as_user(self):
        # type: () -> None
        self._deleted_message_in_missed_stream_messages(True)

    def test_deleted_message_in_missed_stream_messages(self):
        # type: () -> None
        self._deleted_message_in_missed_stream_messages(False)

    @override_settings(SEND_MISSED_MESSAGE_EMAILS_AS_USER=True)
    def test_deleted_message_in_personal_missed_stream_messages_as_user(self):
        # type: () -> None
        self._deleted_message_in_personal_missed_stream_messages(True)

    def test_deleted_message_in_personal_missed_stream_messages(self):
        # type: () -> None
        self._deleted_message_in_personal_missed_stream_messages(False)

    @override_settings(SEND_MISSED_MESSAGE_EMAILS_AS_USER=True)
    def test_deleted_message_in_huddle_missed_stream_messages_as_user(self):
        # type: () -> None
        self._deleted_message_in_huddle_missed_stream_messages(True)

    def test_deleted_message_in_huddle_missed_stream_messages(self):
        # type: () -> None
        self._deleted_message_in_huddle_missed_stream_messages(False)

    @patch('zerver.lib.email_mirror.generate_random_token')
    def test_realm_emoji_in_missed_message(self, mock_random_token):
        # type: (MagicMock) -> None
        tokens = self._get_tokens()
        mock_random_token.side_effect = tokens

        msg_id = self.send_message(self.example_email('othello'), self.example_email('hamlet'),
                                   Recipient.PERSONAL,
                                   'Extremely personal message with a realm emoji :green_tick:!')
        body = '<img alt=":green_tick:" height="20px" src="http://testserver/user_avatars/1/emoji/green_tick.png" title="green tick">'
        subject = 'Othello, the Moor of Venice sent you a message'
        reply_to_name = 'Othello, the Moor of Venice'
        self._test_cases(tokens, msg_id, body, subject, reply_to_name, send_as_user=False, verify_html_body=True)

    @patch('zerver.lib.email_mirror.generate_random_token')
    def test_stream_link_in_missed_message(self, mock_random_token):
        # type: (MagicMock) -> None
        tokens = self._get_tokens()
        mock_random_token.side_effect = tokens

        msg_id = self.send_message(self.example_email('othello'), self.example_email('hamlet'),
                                   Recipient.PERSONAL,
                                   'Come and join us in #**Verona**.')
        body = '<a class="stream" data-stream-id="5" href="http://testserver/#narrow/stream/Verona">#Verona</a'
        subject = 'Othello, the Moor of Venice sent you a message'
        reply_to_name = 'Othello, the Moor of Venice'
        self._test_cases(tokens, msg_id, body, subject, reply_to_name, send_as_user=False, verify_html_body=True)
