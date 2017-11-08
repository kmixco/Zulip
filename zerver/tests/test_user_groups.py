# -*- coding: utf-8 -*-
from typing import Any, List, Optional, Text

import django
import mock

from zerver.lib.test_classes import ZulipTestCase
from zerver.lib.user_groups import (
    check_add_user_to_user_group,
    check_remove_user_from_user_group,
    create_user_group,
    get_user_groups,
    user_groups_in_realm,
)
from zerver.models import UserProfile, UserGroup, get_realm, Realm

class UserGroupTestCase(ZulipTestCase):
    def create_user_group_for_test(self, group_name,
                                   realm=get_realm('zulip')):
        # type: (Text, Realm) -> UserGroup
        members = [self.example_user('othello')]
        return create_user_group(group_name, members, realm)

    def test_user_groups_in_realm(self):
        # type: () -> None
        realm = get_realm('zulip')
        self.assertEqual(len(user_groups_in_realm(realm)), 0)
        self.create_user_group_for_test('support')
        user_groups = user_groups_in_realm(realm)
        self.assertEqual(len(user_groups), 1)
        self.assertEqual(user_groups[0].name, 'support')

    def test_get_user_groups(self):
        # type: () -> None
        othello = self.example_user('othello')
        self.create_user_group_for_test('support')
        user_groups = get_user_groups(othello)
        self.assertEqual(len(user_groups), 1)
        self.assertEqual(user_groups[0].name, 'support')

    def test_check_add_user_to_user_group(self):
        # type: () -> None
        user_group = self.create_user_group_for_test('support')
        hamlet = self.example_user('hamlet')
        self.assertTrue(check_add_user_to_user_group(hamlet, user_group))
        self.assertFalse(check_add_user_to_user_group(hamlet, user_group))

    def test_check_remove_user_from_user_group(self):
        # type: () -> None
        user_group = self.create_user_group_for_test('support')
        othello = self.example_user('othello')
        self.assertTrue(check_remove_user_from_user_group(othello, user_group))
        self.assertFalse(check_remove_user_from_user_group(othello, user_group))

        with mock.patch('zerver.lib.user_groups.remove_user_from_user_group',
                        side_effect=Exception):
            self.assertFalse(check_remove_user_from_user_group(othello, user_group))
