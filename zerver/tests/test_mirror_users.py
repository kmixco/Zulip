from typing import Any, List
from unittest import mock

from django.db import IntegrityError
from django.utils.timezone import now as timezone_now

from zerver.lib.actions import create_mirror_user_if_needed
from zerver.lib.create_user import create_user_profile
from zerver.lib.test_classes import ZulipTestCase
from zerver.lib.test_helpers import reset_emails_in_zulip_realm
from zerver.models import UserProfile, get_client, get_realm, get_user
from zerver.views.message_send import InvalidMirrorInput, create_mirrored_message_users


class MirroredMessageUsersTest(ZulipTestCase):
    def test_invalid_client(self) -> None:
        user = self.example_user("hamlet")
        sender = user

        recipients: List[str] = []

        message_type = "private"
        client = get_client("banned_mirror")

        with self.assertRaises(InvalidMirrorInput):
            create_mirrored_message_users(client, user, recipients, sender.email, message_type)

    def test_invalid_email(self) -> None:
        invalid_email = "alice AT example.com"
        recipients = [invalid_email]

        # We use an MIT user here to maximize code coverage
        user = self.mit_user("starnine")
        sender = user

        message_type = "private"

        for client_name in ["zephyr_mirror", "irc_mirror", "jabber_mirror"]:
            client = get_client(client_name)

            with self.assertRaises(InvalidMirrorInput):
                create_mirrored_message_users(client, user, recipients, sender.email, message_type)

    @mock.patch(
        "DNS.dnslookup",
        return_value=[["sipbtest:*:20922:101:Fred Sipb,,,:/mit/sipbtest:/bin/athena/tcsh"]],
    )
    def test_zephyr_mirror_new_recipient(self, ignored: object) -> None:
        """Test mirror dummy user creation for PM recipients"""
        user = self.mit_user("starnine")
        sender = self.mit_user("sipbtest")
        new_user_email = "bob_the_new_user@mit.edu"
        new_user_realm = get_realm("zephyr")

        recipients = [user.email, new_user_email]

        message_type = "private"
        client = get_client("zephyr_mirror")

        mirror_sender = create_mirrored_message_users(
            client, user, recipients, sender.email, message_type
        )

        self.assertEqual(mirror_sender, sender)

        realm_users = UserProfile.objects.filter(realm=sender.realm)
        realm_emails = {user.email for user in realm_users}
        self.assertIn(user.email, realm_emails)
        self.assertIn(new_user_email, realm_emails)

        bob = get_user(new_user_email, new_user_realm)
        self.assertTrue(bob.is_mirror_dummy)

    @mock.patch(
        "DNS.dnslookup",
        return_value=[["sipbtest:*:20922:101:Fred Sipb,,,:/mit/sipbtest:/bin/athena/tcsh"]],
    )
    def test_zephyr_mirror_new_sender(self, ignored: object) -> None:
        """Test mirror dummy user creation for sender when sending to stream"""
        user = self.mit_user("starnine")
        sender_email = "new_sender@mit.edu"

        recipients = ["stream_name"]

        message_type = "stream"
        client = get_client("zephyr_mirror")

        mirror_sender = create_mirrored_message_users(
            client, user, recipients, sender_email, message_type
        )

        assert mirror_sender is not None
        self.assertEqual(mirror_sender.email, sender_email)
        self.assertTrue(mirror_sender.is_mirror_dummy)

    def test_irc_mirror(self) -> None:
        reset_emails_in_zulip_realm()

        user = self.example_user("hamlet")
        sender = user

        recipients = [
            self.nonreg_email("alice"),
            "bob@irc.zulip.com",
            self.nonreg_email("cordelia"),
        ]

        message_type = "private"
        client = get_client("irc_mirror")

        mirror_sender = create_mirrored_message_users(
            client, user, recipients, sender.email, message_type
        )

        self.assertEqual(mirror_sender, sender)

        realm_users = UserProfile.objects.filter(realm=sender.realm)
        realm_emails = {user.email for user in realm_users}
        self.assertIn(self.nonreg_email("alice"), realm_emails)
        self.assertIn("bob@irc.zulip.com", realm_emails)

        bob = get_user("bob@irc.zulip.com", sender.realm)
        self.assertTrue(bob.is_mirror_dummy)

    def test_jabber_mirror(self) -> None:
        reset_emails_in_zulip_realm()

        user = self.example_user("hamlet")
        sender = user

        recipients = [
            self.nonreg_email("alice"),
            self.nonreg_email("bob"),
            self.nonreg_email("cordelia"),
        ]

        message_type = "private"
        client = get_client("jabber_mirror")

        mirror_sender = create_mirrored_message_users(
            client, user, recipients, sender.email, message_type
        )

        self.assertEqual(mirror_sender, sender)

        realm_users = UserProfile.objects.filter(realm=sender.realm)
        realm_emails = {user.email for user in realm_users}
        self.assertIn(self.nonreg_email("alice"), realm_emails)
        self.assertIn(self.nonreg_email("bob"), realm_emails)

        bob = get_user(self.nonreg_email("bob"), sender.realm)
        self.assertTrue(bob.is_mirror_dummy)

    def test_create_mirror_user_despite_race(self) -> None:
        realm = get_realm("zulip")

        email = "fred@example.com"

        email_to_full_name = lambda email: "fred"

        def create_user(**kwargs: Any) -> UserProfile:
            self.assertEqual(kwargs["full_name"], "fred")
            self.assertEqual(kwargs["email"], email)
            self.assertEqual(kwargs["active"], False)
            self.assertEqual(kwargs["is_mirror_dummy"], True)
            # We create an actual user here to simulate a race.
            # We use the minimal, un-mocked function.
            kwargs["bot_type"] = None
            kwargs["bot_owner"] = None
            kwargs["tos_version"] = None
            kwargs["timezone"] = timezone_now()
            create_user_profile(**kwargs).save()
            raise IntegrityError()

        with mock.patch("zerver.lib.actions.create_user", side_effect=create_user) as m:
            mirror_fred_user = create_mirror_user_if_needed(
                realm,
                email,
                email_to_full_name,
            )

        self.assertEqual(mirror_fred_user.delivery_email, email)
        m.assert_called()
