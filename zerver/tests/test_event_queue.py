import mock
import ujson

from django.http import HttpRequest, HttpResponse
from typing import Any, Callable, Dict, Tuple

from zerver.lib.test_classes import ZulipTestCase
from zerver.lib.test_helpers import POSTRequestMock
from zerver.models import Recipient, Subscription, UserProfile, get_stream
from zerver.tornado.event_queue import maybe_enqueue_notifications, \
    get_client_descriptor, missedmessage_hook
from zerver.tornado.views import get_events_backend

class MissedMessageNotificationsTest(ZulipTestCase):
    """Tests the logic for when missed-message notifications
    should be triggered, based on user settings"""
    def check_will_notify(self, *args, **kwargs):
        # type: (*Any, **Any) -> Tuple[str, str]
        email_notice = None
        mobile_notice = None
        with mock.patch("zerver.tornado.event_queue.queue_json_publish") as mock_queue_publish:
            notified = maybe_enqueue_notifications(*args, **kwargs)
            if notified is None:
                notified = {}
            for entry in mock_queue_publish.call_args_list:
                args = entry[0]
                if args[0] == "missedmessage_mobile_notifications":
                    mobile_notice = args[1]
                if args[0] == "missedmessage_emails":
                    email_notice = args[1]

            # Now verify the return value matches the queue actions
            if email_notice:
                self.assertTrue(notified['email_notified'])
            else:
                self.assertFalse(notified.get('email_notified', False))
            if mobile_notice:
                self.assertTrue(notified['push_notified'])
            else:
                self.assertFalse(notified.get('push_notified', False))
        return email_notice, mobile_notice

    def test_enqueue_notifications(self):
        # type: () -> None
        user_profile = self.example_user("hamlet")
        message_id = 32

        # Boring message doesn't send a notice
        email_notice, mobile_notice = self.check_will_notify(
            user_profile.id, message_id, private_message=False,
            mentioned=False, stream_push_notify=False, stream_name=None,
            always_push_notify=False, idle=True)
        self.assertTrue(email_notice is None)
        self.assertTrue(mobile_notice is None)

        # Private message sends a notice
        email_notice, mobile_notice = self.check_will_notify(
            user_profile.id, message_id, private_message=True,
            mentioned=False, stream_push_notify=False, stream_name=None,
            always_push_notify=False, idle=True)
        self.assertTrue(email_notice is not None)
        self.assertTrue(mobile_notice is not None)

        # Mention sends a notice
        email_notice, mobile_notice = self.check_will_notify(
            user_profile.id, message_id, private_message=False,
            mentioned=True, stream_push_notify=False, stream_name=None,
            always_push_notify=False, idle=True)
        self.assertTrue(email_notice is not None)
        self.assertTrue(mobile_notice is not None)

        # stream_push_notify pushes but doesn't email
        email_notice, mobile_notice = self.check_will_notify(
            user_profile.id, message_id, private_message=False,
            mentioned=False, stream_push_notify=True, stream_name="Denmark",
            always_push_notify=False, idle=True)
        self.assertTrue(email_notice is None)
        self.assertTrue(mobile_notice is not None)

        # Private message doesn't send a notice if not idle
        email_notice, mobile_notice = self.check_will_notify(
            user_profile.id, message_id, private_message=True,
            mentioned=False, stream_push_notify=False, stream_name=None,
            always_push_notify=False, idle=False)
        self.assertTrue(email_notice is None)
        self.assertTrue(mobile_notice is None)

        # Private message sends push but not email if not idle but always_push_notify
        email_notice, mobile_notice = self.check_will_notify(
            user_profile.id, message_id, private_message=True,
            mentioned=False, stream_push_notify=False, stream_name=None,
            always_push_notify=True, idle=False)
        self.assertTrue(email_notice is None)
        self.assertTrue(mobile_notice is not None)

    def tornado_call(self, view_func, user_profile, post_data):
        # type: (Callable[[HttpRequest, UserProfile], HttpResponse], UserProfile, Dict[str, Any]) -> HttpResponse
        request = POSTRequestMock(post_data, user_profile)
        return view_func(request, user_profile)

    def test_end_to_end_missedmessage_hook(self):
        # type: () -> None
        """Tests what arguments missedmessage_hook passes into maybe_enqueue_notifications.
        Combined with the previous test, this ensures that the missedmessage_hook is correct"""
        user_profile = self.example_user('hamlet')
        email = user_profile.email
        self.login(email)

        result = self.tornado_call(get_events_backend, user_profile,
                                   {"apply_markdown": ujson.dumps(True),
                                    "event_types": ujson.dumps(["message"]),
                                    "user_client": "website",
                                    "dont_block": ujson.dumps(True),
                                    })
        self.assert_json_success(result)
        queue_id = ujson.loads(result.content)["queue_id"]
        client_descriptor = get_client_descriptor(queue_id)

        with mock.patch("zerver.tornado.event_queue.maybe_enqueue_notifications") as mock_enqueue:
            # To test the missed_message hook, we first need to send a message
            msg_id = self.send_message(self.example_email("iago"), "Denmark", Recipient.STREAM)

            # Verify that nothing happens if you call it as not the last client
            missedmessage_hook(user_profile.id, client_descriptor, False)
            mock_enqueue.assert_not_called()

            # Now verify that we called the appropriate enqueue function
            missedmessage_hook(user_profile.id, client_descriptor, True)
            mock_enqueue.assert_called_once()
            args_list = mock_enqueue.call_args_list[0][0]

            self.assertEqual(args_list, (user_profile.id, msg_id, False, False, False, None, False, True))

        # Clear the event queue, before repeating with a private message
        client_descriptor.event_queue.pop()
        self.assertTrue(client_descriptor.event_queue.empty())
        msg_id = self.send_message(self.example_email("iago"), [email], Recipient.PERSONAL)
        with mock.patch("zerver.tornado.event_queue.maybe_enqueue_notifications") as mock_enqueue:
            missedmessage_hook(user_profile.id, client_descriptor, True)
            mock_enqueue.assert_called_once()
            args_list = mock_enqueue.call_args_list[0][0]

            self.assertEqual(args_list, (user_profile.id, msg_id, False, False, False, None, False, True))

        # Clear the event queue, now repeat with a mention
        client_descriptor.event_queue.pop()
        self.assertTrue(client_descriptor.event_queue.empty())
        msg_id = self.send_message(self.example_email("iago"), "Denmark", Recipient.STREAM,
                                   content="@**King Hamlet** what's up?")
        with mock.patch("zerver.tornado.event_queue.maybe_enqueue_notifications") as mock_enqueue:
            # Clear the event queue, before repeating with a private message
            missedmessage_hook(user_profile.id, client_descriptor, True)
            mock_enqueue.assert_called_once()
            args_list = mock_enqueue.call_args_list[0][0]

            self.assertEqual(args_list, (user_profile.id, msg_id, False, True, False, None, False, True))
