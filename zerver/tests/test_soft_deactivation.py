# -*- coding: utf-8 -*-
from __future__ import absolute_import

from django.utils.timezone import now as timezone_now

from zerver.lib.soft_deactivation import (
    do_soft_deactivate_user,
    do_soft_deactivate_users,
    get_users_for_soft_deactivation,
    do_soft_activate_users
)
from zerver.lib.test_classes import ZulipTestCase
from zerver.models import Client, UserProfile, UserActivity, get_realm

class UserSoftDeactivationTests(ZulipTestCase):

    def test_do_soft_deactivate_user(self):
        # type: () -> None
        user = self.example_user('hamlet')
        self.assertFalse(user.long_term_idle)

        do_soft_deactivate_user(user)

        user.refresh_from_db()
        self.assertTrue(user.long_term_idle)

    def test_do_soft_deactivate_users(self):
        # type: () -> None
        users = [
            self.example_user('hamlet'),
            self.example_user('iago'),
            self.example_user('cordelia'),
        ]
        for user in users:
            self.assertFalse(user.long_term_idle)

        do_soft_deactivate_users(users)

        for user in users:
            user.refresh_from_db()
            self.assertTrue(user.long_term_idle)

    def test_get_users_for_soft_deactivation(self):
        # type: () -> None
        users = [
            self.example_user('hamlet'),
            self.example_user('iago'),
            self.example_user('cordelia'),
            self.example_user('ZOE'),
            self.example_user('othello'),
            self.example_user('prospero'),
            self.example_user('aaron'),
        ]
        client, _ = Client.objects.get_or_create(name='website')
        query = '/json/users/me/pointer'
        last_visit = timezone_now()
        count = 150
        for user_profile in UserProfile.objects.all():
            UserActivity.objects.get_or_create(
                user_profile=user_profile,
                client=client,
                query=query,
                count=count,
                last_visit=last_visit
            )
        realm = get_realm('zulip')
        users_to_deactivate = get_users_for_soft_deactivation(realm, -1)

        self.assert_length(users_to_deactivate, 7)
        for user in users_to_deactivate:
            self.assertTrue(user in users)

    def test_do_soft_activate_users(self):
        # type: () -> None
        users = [
            self.example_user('hamlet'),
            self.example_user('iago'),
            self.example_user('cordelia'),
        ]
        do_soft_deactivate_users(users)
        for user in users:
            self.assertTrue(user.long_term_idle)

        do_soft_activate_users(users)

        for user in users:
            user.refresh_from_db()
            self.assertFalse(user.long_term_idle)
