import calendar
import datetime
import urllib
from datetime import timedelta
from typing import Any
from unittest.mock import patch

import orjson
import pytz
from django.conf import settings
from django.http import HttpResponse
from django.test import override_settings
from django.utils.timezone import now as timezone_now

from corporate.models import Customer, CustomerPlan
from zerver.lib.actions import change_user_is_active, do_change_plan_type, do_create_user
from zerver.lib.compatibility import LAST_SERVER_UPGRADE_TIME, is_outdated_server
from zerver.lib.home import (
    get_billing_info,
    get_furthest_read_time,
    promote_sponsoring_zulip_in_realm,
)
from zerver.lib.soft_deactivation import do_soft_deactivate_users
from zerver.lib.test_classes import ZulipTestCase
from zerver.lib.test_helpers import get_user_messages, queries_captured
from zerver.models import (
    DefaultStream,
    Draft,
    Realm,
    UserActivity,
    UserProfile,
    flush_per_request_caches,
    get_realm,
    get_stream,
    get_system_bot,
    get_user,
)
from zerver.worker.queue_processors import UserActivityWorker

logger_string = "zulip.soft_deactivation"


class HomeTest(ZulipTestCase):

    # Keep this list sorted!!!
    expected_page_params_keys = [
        "alert_words",
        "apps_page_url",
        "avatar_source",
        "avatar_url",
        "avatar_url_medium",
        "bot_types",
        "can_create_private_streams",
        "can_create_public_streams",
        "can_create_streams",
        "can_create_web_public_streams",
        "can_invite_others_to_realm",
        "can_subscribe_other_users",
        "corporate_enabled",
        "cross_realm_bots",
        "custom_profile_field_types",
        "custom_profile_fields",
        "delivery_email",
        "development_environment",
        "drafts",
        "email",
        "event_queue_longpoll_timeout_seconds",
        "first_in_realm",
        "full_name",
        "furthest_read_time",
        "giphy_api_key",
        "giphy_rating_options",
        "has_zoom_token",
        "hotspots",
        "insecure_desktop_app",
        "is_admin",
        "is_billing_admin",
        "is_guest",
        "is_moderator",
        "is_owner",
        "is_spectator",
        "jitsi_server_url",
        "language_list",
        "last_event_id",
        "login_page",
        "max_avatar_file_size_mib",
        "max_file_upload_size_mib",
        "max_icon_file_size_mib",
        "max_logo_file_size_mib",
        "max_message_id",
        "max_message_length",
        "max_stream_description_length",
        "max_stream_name_length",
        "max_topic_length",
        "muted_topics",
        "muted_users",
        "narrow",
        "narrow_stream",
        "needs_tutorial",
        "never_subscribed",
        "no_event_queue",
        "password_min_guesses",
        "password_min_length",
        "presences",
        "promote_sponsoring_zulip",
        "prompt_for_invites",
        "queue_id",
        "realm_add_custom_emoji_policy",
        "realm_allow_edit_history",
        "realm_allow_message_editing",
        "realm_authentication_methods",
        "realm_available_video_chat_providers",
        "realm_avatar_changes_disabled",
        "realm_bot_creation_policy",
        "realm_bot_domain",
        "realm_bots",
        "realm_community_topic_editing_limit_seconds",
        "realm_create_private_stream_policy",
        "realm_create_public_stream_policy",
        "realm_create_web_public_stream_policy",
        "realm_default_code_block_language",
        "realm_default_external_accounts",
        "realm_default_language",
        "realm_default_stream_groups",
        "realm_default_streams",
        "realm_delete_own_message_policy",
        "realm_description",
        "realm_digest_emails_enabled",
        "realm_digest_weekday",
        "realm_disallow_disposable_email_addresses",
        "realm_domains",
        "realm_edit_topic_policy",
        "realm_email_address_visibility",
        "realm_email_auth_enabled",
        "realm_email_changes_disabled",
        "realm_emails_restricted_to_domains",
        "realm_embedded_bots",
        "realm_emoji",
        "realm_filters",
        "realm_giphy_rating",
        "realm_icon_source",
        "realm_icon_url",
        "realm_incoming_webhook_bots",
        "realm_inline_image_preview",
        "realm_inline_url_embed_preview",
        "realm_invite_required",
        "realm_invite_to_realm_policy",
        "realm_invite_to_stream_policy",
        "realm_is_zephyr_mirror_realm",
        "realm_linkifiers",
        "realm_logo_source",
        "realm_logo_url",
        "realm_mandatory_topics",
        "realm_message_content_allowed_in_email_notifications",
        "realm_message_content_delete_limit_seconds",
        "realm_message_content_edit_limit_seconds",
        "realm_message_retention_days",
        "realm_move_messages_between_streams_policy",
        "realm_name",
        "realm_name_changes_disabled",
        "realm_night_logo_source",
        "realm_night_logo_url",
        "realm_non_active_users",
        "realm_notifications_stream_id",
        "realm_password_auth_enabled",
        "realm_plan_type",
        "realm_playgrounds",
        "realm_presence_disabled",
        "realm_private_message_policy",
        "realm_push_notifications_enabled",
        "realm_send_welcome_emails",
        "realm_signup_notifications_stream_id",
        "realm_upload_quota_mib",
        "realm_uri",
        "realm_user_group_edit_policy",
        "realm_user_groups",
        "realm_user_settings_defaults",
        "realm_users",
        "realm_video_chat_provider",
        "realm_waiting_period_threshold",
        "realm_wildcard_mention_policy",
        "recent_private_conversations",
        "request_language",
        "search_pills_enabled",
        "server_avatar_changes_disabled",
        "server_generation",
        "server_inline_image_preview",
        "server_inline_url_embed_preview",
        "server_name_changes_disabled",
        "server_needs_upgrade",
        "server_timestamp",
        "settings_send_digest_emails",
        "show_billing",
        "show_plans",
        "show_webathena",
        "starred_messages",
        "stop_words",
        "subscriptions",
        "test_suite",
        "translation_data",
        "two_fa_enabled",
        "two_fa_enabled_user",
        "unread_msgs",
        "unsubscribed",
        "upgrade_text_for_wide_organization_logo",
        "user_id",
        "user_settings",
        "user_status",
        "warn_no_email",
        "webpack_public_path",
        "zulip_feature_level",
        "zulip_merge_base",
        "zulip_plan_is_not_limited",
        "zulip_version",
    ]

    def test_home(self) -> None:
        # Keep this list sorted!!!
        html_bits = [
            "start the conversation",
            "Loading...",
            # Verify that the app styles get included
            "app-stubentry.js",
            "data-params",
        ]

        self.login("hamlet")

        # Create bot for realm_bots testing. Must be done before fetching home_page.
        bot_info = {
            "full_name": "The Bot of Hamlet",
            "short_name": "hambot",
        }
        self.client_post("/json/bots", bot_info)

        # Verify succeeds once logged-in
        flush_per_request_caches()
        with queries_captured() as queries:
            with patch("zerver.lib.cache.cache_set") as cache_mock:
                result = self._get_home_page(stream="Denmark")
                self.check_rendered_logged_in_app(result)
        self.assertEqual(
            set(result["Cache-Control"].split(", ")), {"must-revalidate", "no-store", "no-cache"}
        )

        self.assert_length(queries, 44)
        self.assert_length(cache_mock.call_args_list, 5)

        html = result.content.decode()

        for html_bit in html_bits:
            if html_bit not in html:
                raise AssertionError(f"{html_bit} not in result")

        page_params = self._get_page_params(result)

        actual_keys = sorted(str(k) for k in page_params.keys())

        self.assertEqual(actual_keys, self.expected_page_params_keys)

        # TODO: Inspect the page_params data further.
        # print(orjson.dumps(page_params, option=orjson.OPT_INDENT_2).decode())
        realm_bots_expected_keys = [
            "api_key",
            "avatar_url",
            "bot_type",
            "default_all_public_streams",
            "default_events_register_stream",
            "default_sending_stream",
            "email",
            "full_name",
            "is_active",
            "owner_id",
            "services",
            "user_id",
        ]

        realm_bots_actual_keys = sorted(str(key) for key in page_params["realm_bots"][0].keys())
        self.assertEqual(realm_bots_actual_keys, realm_bots_expected_keys)

    def test_home_demo_organization(self) -> None:
        realm = get_realm("zulip")

        # We construct a scheduled deletion date that's definitely in
        # the future, regardless of how long ago the Zulip realm was
        # created.
        realm.demo_organization_scheduled_deletion_date = timezone_now() + datetime.timedelta(
            days=1
        )
        realm.save()
        self.login("hamlet")

        # Verify succeeds once logged-in
        flush_per_request_caches()
        with queries_captured():
            with patch("zerver.lib.cache.cache_set"):
                result = self._get_home_page(stream="Denmark")
                self.check_rendered_logged_in_app(result)

        page_params = self._get_page_params(result)
        actual_keys = sorted(str(k) for k in page_params.keys())
        expected_keys = self.expected_page_params_keys + [
            "demo_organization_scheduled_deletion_date"
        ]

        self.assertEqual(set(actual_keys), set(expected_keys))

    def test_logged_out_home(self) -> None:
        # Redirect to login on first request.
        result = self.client_get("/")
        self.assertEqual(result.status_code, 302)
        self.assertEqual(result.url, "/login/")

        # Tell server that user wants to login anonymously
        # Redirects to load webapp.
        result = self.client_post("/", {"prefers_web_public_view": "true"})
        self.assertEqual(result.status_code, 302)
        self.assertEqual(result.url, "http://zulip.testserver")

        # Always load the web app from then on directly
        result = self.client_get("/")
        self.assertEqual(result.status_code, 200)

        page_params = self._get_page_params(result)
        actual_keys = sorted(str(k) for k in page_params.keys())
        removed_keys = [
            "last_event_id",
            "narrow",
            "narrow_stream",
        ]
        expected_keys = [i for i in self.expected_page_params_keys if i not in removed_keys]
        self.assertEqual(actual_keys, expected_keys)

    def test_home_under_2fa_without_otp_device(self) -> None:
        with self.settings(TWO_FACTOR_AUTHENTICATION_ENABLED=True):
            self.login("iago")
            result = self._get_home_page()
            # Should be successful because otp device is not configured.
            self.check_rendered_logged_in_app(result)

    def test_home_under_2fa_with_otp_device(self) -> None:
        with self.settings(TWO_FACTOR_AUTHENTICATION_ENABLED=True):
            user_profile = self.example_user("iago")
            self.create_default_device(user_profile)
            self.login_user(user_profile)
            result = self._get_home_page()
            # User should not log in because otp device is configured but
            # 2fa login function was not called.
            self.assertEqual(result.status_code, 302)

            self.login_2fa(user_profile)
            result = self._get_home_page()
            # Should be successful after calling 2fa login function.
            self.check_rendered_logged_in_app(result)

    def test_num_queries_for_realm_admin(self) -> None:
        # Verify number of queries for Realm admin isn't much higher than for normal users.
        self.login("iago")
        flush_per_request_caches()
        with queries_captured() as queries:
            with patch("zerver.lib.cache.cache_set") as cache_mock:
                result = self._get_home_page()
                self.check_rendered_logged_in_app(result)
                self.assert_length(cache_mock.call_args_list, 6)
            self.assert_length(queries, 41)

    def test_num_queries_with_streams(self) -> None:
        main_user = self.example_user("hamlet")
        other_user = self.example_user("cordelia")

        realm_id = main_user.realm_id

        self.login_user(main_user)

        # Try to make page-load do extra work for various subscribed
        # streams.
        for i in range(10):
            stream_name = "test_stream_" + str(i)
            stream = self.make_stream(stream_name)
            DefaultStream.objects.create(
                realm_id=realm_id,
                stream_id=stream.id,
            )
            for user in [main_user, other_user]:
                self.subscribe(user, stream_name)

        # Simulate hitting the page the first time to avoid some noise
        # related to initial logins.
        self._get_home_page()

        # Then for the second page load, measure the number of queries.
        flush_per_request_caches()
        with queries_captured() as queries2:
            result = self._get_home_page()

        self.assert_length(queries2, 39)

        # Do a sanity check that our new streams were in the payload.
        html = result.content.decode()
        self.assertIn("test_stream_7", html)

    def _get_home_page(self, **kwargs: Any) -> HttpResponse:
        with patch("zerver.lib.events.request_event_queue", return_value=42), patch(
            "zerver.lib.events.get_user_events", return_value=[]
        ):
            result = self.client_get("/", dict(**kwargs))
        return result

    def _sanity_check(self, result: HttpResponse) -> None:
        """
        Use this for tests that are geared toward specific edge cases, but
        which still want the home page to load properly.
        """
        html = result.content.decode()
        if "start a conversation" not in html:
            raise AssertionError("Home page probably did not load.")

    def test_terms_of_service(self) -> None:
        user = self.example_user("hamlet")
        self.login_user(user)

        for user_tos_version in [None, "1.1", "2.0.3.4"]:
            user.tos_version = user_tos_version
            user.save()

            with self.settings(TERMS_OF_SERVICE="whatever"), self.settings(TOS_VERSION="99.99"):

                result = self.client_get("/", dict(stream="Denmark"))

            html = result.content.decode()
            self.assertIn("Accept the new Terms of Service", html)

    def test_banned_desktop_app_versions(self) -> None:
        user = self.example_user("hamlet")
        self.login_user(user)

        result = self.client_get("/", HTTP_USER_AGENT="ZulipElectron/2.3.82")
        html = result.content.decode()
        self.assertIn("You are using old version of the Zulip desktop", html)

    def test_unsupported_browser(self) -> None:
        user = self.example_user("hamlet")
        self.login_user(user)

        # currently we don't support IE, so some of IE's user agents are added.
        unsupported_user_agents = [
            "Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.2)",
            "Mozilla/5.0 (Windows NT 10.0; Trident/7.0; rv:11.0) like Gecko",
            "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; Trident/4.0)",
        ]
        for user_agent in unsupported_user_agents:
            result = self.client_get("/", HTTP_USER_AGENT=user_agent)
            html = result.content.decode()
            self.assertIn("Internet Explorer is not supported by Zulip.", html)

    def test_terms_of_service_first_time_template(self) -> None:
        user = self.example_user("hamlet")
        self.login_user(user)

        user.tos_version = None
        user.save()

        with self.settings(FIRST_TIME_TOS_TEMPLATE="hello.html"), self.settings(
            TOS_VERSION="99.99"
        ):
            result = self.client_post("/accounts/accept_terms/")
            self.assertEqual(result.status_code, 200)
            self.assert_in_response("I agree to the", result)
            self.assert_in_response("Chat for distributed teams", result)

    def test_accept_terms_of_service(self) -> None:
        self.login("hamlet")

        result = self.client_post("/accounts/accept_terms/")
        self.assertEqual(result.status_code, 200)
        self.assert_in_response("I agree to the", result)

        result = self.client_post("/accounts/accept_terms/", {"terms": True})
        self.assertEqual(result.status_code, 302)
        self.assertEqual(result["Location"], "/")

    def test_bad_narrow(self) -> None:
        self.login("hamlet")
        with self.assertLogs(level="WARNING") as m:
            result = self._get_home_page(stream="Invalid Stream")
            self.assertEqual(m.output, ["WARNING:root:Invalid narrow requested, ignoring"])
        self._sanity_check(result)

    def test_topic_narrow(self) -> None:
        self.login("hamlet")
        result = self._get_home_page(stream="Denmark", topic="lunch")
        self._sanity_check(result)
        html = result.content.decode()
        self.assertIn("lunch", html)
        self.assertEqual(
            set(result["Cache-Control"].split(", ")), {"must-revalidate", "no-store", "no-cache"}
        )

    def test_notifications_stream(self) -> None:
        realm = get_realm("zulip")
        realm.notifications_stream_id = get_stream("Denmark", realm).id
        realm.save()
        self.login("hamlet")
        result = self._get_home_page()
        page_params = self._get_page_params(result)
        self.assertEqual(
            page_params["realm_notifications_stream_id"], get_stream("Denmark", realm).id
        )

    def create_bot(self, owner: UserProfile, bot_email: str, bot_name: str) -> UserProfile:
        user = do_create_user(
            email=bot_email,
            password="123",
            realm=owner.realm,
            full_name=bot_name,
            bot_type=UserProfile.DEFAULT_BOT,
            bot_owner=owner,
            acting_user=None,
        )
        return user

    def create_non_active_user(self, realm: Realm, email: str, name: str) -> UserProfile:
        user = do_create_user(
            email=email, password="123", realm=realm, full_name=name, acting_user=None
        )

        # Doing a full-stack deactivation would be expensive here,
        # and we really only need to flip the flag to get a valid
        # test.
        change_user_is_active(user, False)
        return user

    def test_signup_notifications_stream(self) -> None:
        realm = get_realm("zulip")
        realm.signup_notifications_stream = get_stream("Denmark", realm)
        realm.save()
        self.login("hamlet")
        result = self._get_home_page()
        page_params = self._get_page_params(result)
        self.assertEqual(
            page_params["realm_signup_notifications_stream_id"], get_stream("Denmark", realm).id
        )

    def test_people(self) -> None:
        hamlet = self.example_user("hamlet")
        realm = get_realm("zulip")
        self.login_user(hamlet)

        bots = {}
        for i in range(3):
            bots[i] = self.create_bot(
                owner=hamlet,
                bot_email=f"bot-{i}@zulip.com",
                bot_name=f"Bot {i}",
            )

        for i in range(3):
            defunct_user = self.create_non_active_user(
                realm=realm,
                email=f"defunct-{i}@zulip.com",
                name=f"Defunct User {i}",
            )

        result = self._get_home_page()
        page_params = self._get_page_params(result)

        """
        We send three lists of users.  The first two below are disjoint
        lists of users, and the records we send for them have identical
        structure.

        The realm_bots bucket is somewhat redundant, since all bots will
        be in one of the first two buckets.  They do include fields, however,
        that normal users don't care about, such as default_sending_stream.
        """

        buckets = [
            "realm_users",
            "realm_non_active_users",
            "realm_bots",
        ]

        for field in buckets:
            users = page_params[field]
            self.assertGreaterEqual(len(users), 3, field)
            for rec in users:
                self.assertEqual(rec["user_id"], get_user(rec["email"], realm).id)
                if field == "realm_bots":
                    self.assertNotIn("is_bot", rec)
                    self.assertIn("is_active", rec)
                    self.assertIn("owner_id", rec)
                else:
                    self.assertIn("is_bot", rec)
                    self.assertNotIn("is_active", rec)

        active_ids = {p["user_id"] for p in page_params["realm_users"]}
        non_active_ids = {p["user_id"] for p in page_params["realm_non_active_users"]}
        bot_ids = {p["user_id"] for p in page_params["realm_bots"]}

        self.assertIn(hamlet.id, active_ids)
        self.assertIn(defunct_user.id, non_active_ids)

        # Bots can show up in multiple buckets.
        self.assertIn(bots[2].id, bot_ids)
        self.assertIn(bots[2].id, active_ids)

        # Make sure nobody got mis-bucketed.
        self.assertNotIn(hamlet.id, non_active_ids)
        self.assertNotIn(defunct_user.id, active_ids)

        cross_bots = page_params["cross_realm_bots"]
        self.assert_length(cross_bots, 3)
        cross_bots.sort(key=lambda d: d["email"])
        for cross_bot in cross_bots:
            # These are either nondeterministic or boring
            del cross_bot["timezone"]
            del cross_bot["avatar_url"]
            del cross_bot["date_joined"]

        admin_realm = get_realm(settings.SYSTEM_BOT_REALM)
        cross_realm_notification_bot = self.notification_bot(admin_realm)
        cross_realm_email_gateway_bot = get_system_bot(settings.EMAIL_GATEWAY_BOT, admin_realm.id)
        cross_realm_welcome_bot = get_system_bot(settings.WELCOME_BOT, admin_realm.id)

        by_email = lambda d: d["email"]

        self.assertEqual(
            sorted(cross_bots, key=by_email),
            sorted(
                [
                    dict(
                        avatar_version=cross_realm_email_gateway_bot.avatar_version,
                        bot_owner_id=None,
                        bot_type=1,
                        email=cross_realm_email_gateway_bot.email,
                        user_id=cross_realm_email_gateway_bot.id,
                        full_name=cross_realm_email_gateway_bot.full_name,
                        is_active=True,
                        is_bot=True,
                        is_admin=False,
                        is_owner=False,
                        is_billing_admin=False,
                        role=cross_realm_email_gateway_bot.role,
                        is_system_bot=True,
                        is_guest=False,
                    ),
                    dict(
                        avatar_version=cross_realm_notification_bot.avatar_version,
                        bot_owner_id=None,
                        bot_type=1,
                        email=cross_realm_notification_bot.email,
                        user_id=cross_realm_notification_bot.id,
                        full_name=cross_realm_notification_bot.full_name,
                        is_active=True,
                        is_bot=True,
                        is_admin=False,
                        is_owner=False,
                        is_billing_admin=False,
                        role=cross_realm_notification_bot.role,
                        is_system_bot=True,
                        is_guest=False,
                    ),
                    dict(
                        avatar_version=cross_realm_welcome_bot.avatar_version,
                        bot_owner_id=None,
                        bot_type=1,
                        email=cross_realm_welcome_bot.email,
                        user_id=cross_realm_welcome_bot.id,
                        full_name=cross_realm_welcome_bot.full_name,
                        is_active=True,
                        is_bot=True,
                        is_admin=False,
                        is_owner=False,
                        is_billing_admin=False,
                        role=cross_realm_welcome_bot.role,
                        is_system_bot=True,
                        is_guest=False,
                    ),
                ],
                key=by_email,
            ),
        )

    def test_new_stream(self) -> None:
        user_profile = self.example_user("hamlet")
        stream_name = "New stream"
        self.subscribe(user_profile, stream_name)
        self.login_user(user_profile)
        result = self._get_home_page(stream=stream_name)
        page_params = self._get_page_params(result)
        self.assertEqual(page_params["narrow_stream"], stream_name)
        self.assertEqual(page_params["narrow"], [dict(operator="stream", operand=stream_name)])
        self.assertEqual(page_params["max_message_id"], -1)

    def test_get_billing_info(self) -> None:
        user = self.example_user("desdemona")
        user.role = UserProfile.ROLE_REALM_OWNER
        user.save(update_fields=["role"])
        # realm owner, but no CustomerPlan and realm plan_type SELF_HOSTED -> neither billing link or plans
        with self.settings(CORPORATE_ENABLED=True):
            billing_info = get_billing_info(user)
        self.assertFalse(billing_info.show_billing)
        self.assertFalse(billing_info.show_plans)

        # realm owner, with inactive CustomerPlan and realm plan_type SELF_HOSTED -> show only billing link
        customer = Customer.objects.create(realm=get_realm("zulip"), stripe_customer_id="cus_id")
        CustomerPlan.objects.create(
            customer=customer,
            billing_cycle_anchor=timezone_now(),
            billing_schedule=CustomerPlan.ANNUAL,
            next_invoice_date=timezone_now(),
            tier=CustomerPlan.STANDARD,
            status=CustomerPlan.ENDED,
        )
        with self.settings(CORPORATE_ENABLED=True):
            billing_info = get_billing_info(user)
        self.assertTrue(billing_info.show_billing)
        self.assertFalse(billing_info.show_plans)

        # realm owner, with inactive CustomerPlan and realm plan_type LIMITED -> show billing link and plans
        do_change_plan_type(user.realm, Realm.PLAN_TYPE_LIMITED, acting_user=None)
        with self.settings(CORPORATE_ENABLED=True):
            billing_info = get_billing_info(user)
        self.assertTrue(billing_info.show_billing)
        self.assertTrue(billing_info.show_plans)

        # Always false without CORPORATE_ENABLED
        with self.settings(CORPORATE_ENABLED=False):
            billing_info = get_billing_info(user)
        self.assertFalse(billing_info.show_billing)
        self.assertFalse(billing_info.show_plans)

        # Always false without a UserProfile
        with self.settings(CORPORATE_ENABLED=True):
            billing_info = get_billing_info(None)
        self.assertFalse(billing_info.show_billing)
        self.assertFalse(billing_info.show_plans)

        # realm admin, with CustomerPlan and realm plan_type LIMITED -> show only billing plans
        user.role = UserProfile.ROLE_REALM_ADMINISTRATOR
        user.save(update_fields=["role"])
        with self.settings(CORPORATE_ENABLED=True):
            billing_info = get_billing_info(user)
        self.assertFalse(billing_info.show_billing)
        self.assertTrue(billing_info.show_plans)

        # billing admin, with CustomerPlan and realm plan_type STANDARD -> show only billing link
        user.role = UserProfile.ROLE_MEMBER
        user.is_billing_admin = True
        do_change_plan_type(user.realm, Realm.PLAN_TYPE_STANDARD, acting_user=None)
        user.save(update_fields=["role", "is_billing_admin"])
        with self.settings(CORPORATE_ENABLED=True):
            billing_info = get_billing_info(user)
        self.assertTrue(billing_info.show_billing)
        self.assertFalse(billing_info.show_plans)

        # billing admin, with CustomerPlan and realm plan_type PLUS -> show only billing link
        do_change_plan_type(user.realm, Realm.PLAN_TYPE_PLUS, acting_user=None)
        user.save(update_fields=["role", "is_billing_admin"])
        with self.settings(CORPORATE_ENABLED=True):
            billing_info = get_billing_info(user)
        self.assertTrue(billing_info.show_billing)
        self.assertFalse(billing_info.show_plans)

        # member, with CustomerPlan and realm plan_type STANDARD -> neither billing link or plans
        do_change_plan_type(user.realm, Realm.PLAN_TYPE_STANDARD, acting_user=None)
        user.is_billing_admin = False
        user.save(update_fields=["is_billing_admin"])
        with self.settings(CORPORATE_ENABLED=True):
            billing_info = get_billing_info(user)
        self.assertFalse(billing_info.show_billing)
        self.assertFalse(billing_info.show_plans)

        # guest, with CustomerPlan and realm plan_type SELF_HOSTED -> neither billing link or plans
        user.role = UserProfile.ROLE_GUEST
        user.save(update_fields=["role"])
        do_change_plan_type(user.realm, Realm.PLAN_TYPE_SELF_HOSTED, acting_user=None)
        with self.settings(CORPORATE_ENABLED=True):
            billing_info = get_billing_info(user)
        self.assertFalse(billing_info.show_billing)
        self.assertFalse(billing_info.show_plans)

        # billing admin, but no CustomerPlan and realm plan_type SELF_HOSTED -> neither billing link or plans
        user.role = UserProfile.ROLE_MEMBER
        user.is_billing_admin = True
        user.save(update_fields=["role", "is_billing_admin"])
        CustomerPlan.objects.all().delete()
        with self.settings(CORPORATE_ENABLED=True):
            billing_info = get_billing_info(user)
        self.assertFalse(billing_info.show_billing)
        self.assertFalse(billing_info.show_plans)

        # billing admin, with sponsorship pending and relam plan_type SELF_HOSTED -> show only billing link
        customer.sponsorship_pending = True
        customer.save(update_fields=["sponsorship_pending"])
        with self.settings(CORPORATE_ENABLED=True):
            billing_info = get_billing_info(user)
        self.assertTrue(billing_info.show_billing)
        self.assertFalse(billing_info.show_plans)

        # billing admin, no customer object and relam plan_type SELF_HOSTED -> neither billing link or plans
        customer.delete()
        with self.settings(CORPORATE_ENABLED=True):
            billing_info = get_billing_info(user)
        self.assertFalse(billing_info.show_billing)
        self.assertFalse(billing_info.show_plans)

    def test_promote_sponsoring_zulip_in_realm(self) -> None:
        realm = get_realm("zulip")

        do_change_plan_type(realm, Realm.PLAN_TYPE_STANDARD_FREE, acting_user=None)
        promote_zulip = promote_sponsoring_zulip_in_realm(realm)
        self.assertTrue(promote_zulip)

        with self.settings(PROMOTE_SPONSORING_ZULIP=False):
            promote_zulip = promote_sponsoring_zulip_in_realm(realm)
        self.assertFalse(promote_zulip)

        do_change_plan_type(realm, Realm.PLAN_TYPE_STANDARD_FREE, acting_user=None)
        promote_zulip = promote_sponsoring_zulip_in_realm(realm)
        self.assertTrue(promote_zulip)

        do_change_plan_type(realm, Realm.PLAN_TYPE_LIMITED, acting_user=None)
        promote_zulip = promote_sponsoring_zulip_in_realm(realm)
        self.assertFalse(promote_zulip)

        do_change_plan_type(realm, Realm.PLAN_TYPE_STANDARD, acting_user=None)
        promote_zulip = promote_sponsoring_zulip_in_realm(realm)
        self.assertFalse(promote_zulip)

    def test_desktop_home(self) -> None:
        self.login("hamlet")
        result = self.client_get("/desktop_home")
        self.assertEqual(result.status_code, 301)
        self.assertTrue(result["Location"].endswith("/desktop_home/"))
        result = self.client_get("/desktop_home/")
        self.assertEqual(result.status_code, 302)
        path = urllib.parse.urlparse(result["Location"]).path
        self.assertEqual(path, "/")

    @override_settings(SERVER_UPGRADE_NAG_DEADLINE_DAYS=365)
    def test_is_outdated_server(self) -> None:
        # Check when server_upgrade_nag_deadline > last_server_upgrade_time
        hamlet = self.example_user("hamlet")
        iago = self.example_user("iago")
        now = LAST_SERVER_UPGRADE_TIME.replace(tzinfo=pytz.utc)
        with patch("zerver.lib.compatibility.timezone_now", return_value=now + timedelta(days=10)):
            self.assertEqual(is_outdated_server(iago), False)
            self.assertEqual(is_outdated_server(hamlet), False)
            self.assertEqual(is_outdated_server(None), False)

        with patch("zerver.lib.compatibility.timezone_now", return_value=now + timedelta(days=397)):
            self.assertEqual(is_outdated_server(iago), True)
            self.assertEqual(is_outdated_server(hamlet), True)
            self.assertEqual(is_outdated_server(None), True)

        with patch("zerver.lib.compatibility.timezone_now", return_value=now + timedelta(days=380)):
            self.assertEqual(is_outdated_server(iago), True)
            self.assertEqual(is_outdated_server(hamlet), False)
            self.assertEqual(is_outdated_server(None), False)

    def test_furthest_read_time(self) -> None:
        msg_id = self.send_test_message("hello!", sender_name="iago")

        hamlet = self.example_user("hamlet")
        self.login_user(hamlet)
        self.client_post(
            "/json/messages/flags",
            {"messages": orjson.dumps([msg_id]).decode(), "op": "add", "flag": "read"},
        )

        # Manually process the UserActivity
        now = timezone_now()
        activity_time = calendar.timegm(now.timetuple())
        user_activity_event = {
            "user_profile_id": hamlet.id,
            "client_id": 1,
            "query": "update_message_flags",
            "time": activity_time,
        }

        yesterday = now - timedelta(days=1)
        activity_time_2 = calendar.timegm(yesterday.timetuple())
        user_activity_event_2 = {
            "user_profile_id": hamlet.id,
            "client_id": 2,
            "query": "update_message_flags",
            "time": activity_time_2,
        }
        UserActivityWorker().consume_batch([user_activity_event, user_activity_event_2])

        # verify furthest_read_time is last activity time, irrespective of client
        furthest_read_time = get_furthest_read_time(hamlet)
        self.assertGreaterEqual(furthest_read_time, activity_time)

        # Check when user has no activity
        UserActivity.objects.filter(user_profile=hamlet).delete()
        furthest_read_time = get_furthest_read_time(hamlet)
        self.assertIsNone(furthest_read_time)

        # Check no user profile handling
        furthest_read_time = get_furthest_read_time(None)
        self.assertIsNotNone(furthest_read_time)

    def test_subdomain_homepage(self) -> None:
        self.login("hamlet")
        with self.settings(ROOT_DOMAIN_LANDING_PAGE=True):
            with patch("zerver.views.home.get_subdomain", return_value=""):
                result = self._get_home_page()
            self.assertEqual(result.status_code, 200)
            self.assert_in_response("Chat for distributed teams", result)

            with patch("zerver.views.home.get_subdomain", return_value="subdomain"):
                result = self._get_home_page()
            self._sanity_check(result)

    def send_test_message(
        self,
        content: str,
        sender_name: str = "iago",
        stream_name: str = "Denmark",
        topic_name: str = "foo",
    ) -> int:
        sender = self.example_user(sender_name)
        return self.send_stream_message(sender, stream_name, content=content, topic_name=topic_name)

    def soft_activate_and_get_unread_count(
        self, stream: str = "Denmark", topic: str = "foo"
    ) -> int:
        stream_narrow = self._get_home_page(stream=stream, topic=topic)
        page_params = self._get_page_params(stream_narrow)
        return page_params["unread_msgs"]["count"]

    def test_unread_count_user_soft_deactivation(self) -> None:
        # In this test we make sure if a soft deactivated user had unread
        # messages before deactivation they remain same way after activation.
        long_term_idle_user = self.example_user("hamlet")
        self.login_user(long_term_idle_user)
        message = "Test message 1"
        self.send_test_message(message)
        with queries_captured() as queries:
            self.assertEqual(self.soft_activate_and_get_unread_count(), 1)
        query_count = len(queries)
        user_msg_list = get_user_messages(long_term_idle_user)
        self.assertEqual(user_msg_list[-1].content, message)
        self.logout()

        with self.assertLogs(logger_string, level="INFO") as info_log:
            do_soft_deactivate_users([long_term_idle_user])
        self.assertEqual(
            info_log.output,
            [
                f"INFO:{logger_string}:Soft deactivated user {long_term_idle_user.id}",
                f"INFO:{logger_string}:Soft-deactivated batch of 1 users; 0 remain to process",
            ],
        )

        self.login_user(long_term_idle_user)
        message = "Test message 2"
        self.send_test_message(message)
        idle_user_msg_list = get_user_messages(long_term_idle_user)
        self.assertNotEqual(idle_user_msg_list[-1].content, message)
        with queries_captured() as queries:
            self.assertEqual(self.soft_activate_and_get_unread_count(), 2)
        # Test here for query count to be at least 5 greater than previous count
        # This will assure indirectly that add_missing_messages() was called.
        self.assertGreaterEqual(len(queries) - query_count, 5)
        idle_user_msg_list = get_user_messages(long_term_idle_user)
        self.assertEqual(idle_user_msg_list[-1].content, message)

    def test_multiple_user_soft_deactivations(self) -> None:
        long_term_idle_user = self.example_user("hamlet")
        # We are sending this message to ensure that long_term_idle_user has
        # at least one UserMessage row.
        self.send_test_message("Testing", sender_name="hamlet")
        with self.assertLogs(logger_string, level="INFO") as info_log:
            do_soft_deactivate_users([long_term_idle_user])
        self.assertEqual(
            info_log.output,
            [
                f"INFO:{logger_string}:Soft deactivated user {long_term_idle_user.id}",
                f"INFO:{logger_string}:Soft-deactivated batch of 1 users; 0 remain to process",
            ],
        )

        message = "Test message 1"
        self.send_test_message(message)
        self.login_user(long_term_idle_user)
        with queries_captured() as queries:
            self.assertEqual(self.soft_activate_and_get_unread_count(), 2)
        query_count = len(queries)
        long_term_idle_user.refresh_from_db()
        self.assertFalse(long_term_idle_user.long_term_idle)
        idle_user_msg_list = get_user_messages(long_term_idle_user)
        self.assertEqual(idle_user_msg_list[-1].content, message)

        message = "Test message 2"
        self.send_test_message(message)
        with queries_captured() as queries:
            self.assertEqual(self.soft_activate_and_get_unread_count(), 3)
        # Test here for query count to be at least 5 less than previous count.
        # This will assure add_missing_messages() isn't repeatedly called.
        self.assertGreaterEqual(query_count - len(queries), 5)
        idle_user_msg_list = get_user_messages(long_term_idle_user)
        self.assertEqual(idle_user_msg_list[-1].content, message)
        self.logout()

        with self.assertLogs(logger_string, level="INFO") as info_log:
            do_soft_deactivate_users([long_term_idle_user])
        self.assertEqual(
            info_log.output,
            [
                f"INFO:{logger_string}:Soft deactivated user {long_term_idle_user.id}",
                f"INFO:{logger_string}:Soft-deactivated batch of 1 users; 0 remain to process",
            ],
        )

        message = "Test message 3"
        self.send_test_message(message)
        self.login_user(long_term_idle_user)
        with queries_captured() as queries:
            self.assertEqual(self.soft_activate_and_get_unread_count(), 4)
        query_count = len(queries)
        long_term_idle_user.refresh_from_db()
        self.assertFalse(long_term_idle_user.long_term_idle)
        idle_user_msg_list = get_user_messages(long_term_idle_user)
        self.assertEqual(idle_user_msg_list[-1].content, message)

        message = "Test message 4"
        self.send_test_message(message)
        with queries_captured() as queries:
            self.assertEqual(self.soft_activate_and_get_unread_count(), 5)
        self.assertGreaterEqual(query_count - len(queries), 5)
        idle_user_msg_list = get_user_messages(long_term_idle_user)
        self.assertEqual(idle_user_msg_list[-1].content, message)
        self.logout()

    def test_url_language(self) -> None:
        user = self.example_user("hamlet")
        user.default_language = "es"
        user.save()
        self.login_user(user)
        result = self._get_home_page()
        self.check_rendered_logged_in_app(result)
        with patch("zerver.lib.events.request_event_queue", return_value=42), patch(
            "zerver.lib.events.get_user_events", return_value=[]
        ):
            result = self.client_get("/de/")
        page_params = self._get_page_params(result)
        self.assertEqual(page_params["user_settings"]["default_language"], "es")
        # TODO: Verify that the actual language we're using in the
        # translation data is German.

    def test_translation_data(self) -> None:
        user = self.example_user("hamlet")
        user.default_language = "es"
        user.save()
        self.login_user(user)
        result = self._get_home_page()
        self.check_rendered_logged_in_app(result)

        page_params = self._get_page_params(result)
        self.assertEqual(page_params["user_settings"]["default_language"], "es")

    # TODO: This test would likely be better written as a /register
    # API test with just the drafts event type, to avoid the
    # performance cost of fetching /.
    @override_settings(MAX_DRAFTS_IN_REGISTER_RESPONSE=5)
    def test_limit_drafts(self) -> None:
        draft_objects = []
        hamlet = self.example_user("hamlet")
        base_time = timezone_now()
        initial_count = Draft.objects.count()

        step_value = timedelta(seconds=1)
        # Create 11 drafts.
        # TODO: This would be better done as an API request.
        for i in range(0, settings.MAX_DRAFTS_IN_REGISTER_RESPONSE + 1):
            draft_objects.append(
                Draft(
                    user_profile=hamlet,
                    recipient=None,
                    topic="",
                    content="sample draft",
                    last_edit_time=base_time + i * step_value,
                )
            )
        Draft.objects.bulk_create(draft_objects)

        # Now fetch the drafts part of the initial state and make sure
        # that we only got back settings.MAX_DRAFTS_IN_REGISTER_RESPONSE.
        # No more. Also make sure that the drafts returned are the most
        # recently edited ones.
        self.login("hamlet")
        page_params = self._get_page_params(self._get_home_page())
        self.assertEqual(page_params["user_settings"]["enable_drafts_synchronization"], True)
        self.assert_length(page_params["drafts"], settings.MAX_DRAFTS_IN_REGISTER_RESPONSE)
        self.assertEqual(
            Draft.objects.count(), settings.MAX_DRAFTS_IN_REGISTER_RESPONSE + 1 + initial_count
        )
        # +2 for what's already in the test DB.
        for draft in page_params["drafts"]:
            self.assertNotEqual(draft["timestamp"], base_time)
