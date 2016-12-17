from django.db import models
from django.test import TestCase
from django.utils import timezone

from analytics.lib.counts import CountStat, COUNT_STATS, process_count_stat, \
    zerver_count_user_by_realm, zerver_count_message_by_user, \
    zerver_count_message_by_stream, zerver_count_stream_by_realm, \
    do_fill_count_stat_at_hour, ZerverCountQuery
from analytics.models import BaseCount, InstallationCount, RealmCount, \
    UserCount, StreamCount, FillState, get_fill_state, installation_epoch

from zerver.models import Realm, UserProfile, Message, Stream, Recipient, \
    get_user_profile_by_email, get_client

from datetime import datetime, timedelta

from typing import Any, Type, Optional, Text

class AnalyticsTestCase(TestCase):
    MINUTE = timedelta(seconds = 60)
    HOUR = MINUTE * 60
    DAY = HOUR * 24
    TIME_ZERO = datetime(1988, 3, 14).replace(tzinfo=timezone.utc)
    TIME_LAST_HOUR = TIME_ZERO - HOUR

    def setUp(self):
        # type: () -> None
        self.default_realm = Realm.objects.create(
            string_id='realmtest', name='Realm Test',
            domain='test.analytics', date_created=self.TIME_ZERO - 2*self.DAY)

    # Lightweight creation of users, streams, and messages
    def create_user(self, email, **kwargs):
        # type: (str, **Any) -> UserProfile
        defaults = {
            'date_joined': self.TIME_LAST_HOUR,
            'full_name': 'full_name',
            'short_name': 'short_name',
            'pointer': -1,
            'last_pointer_updater': 'seems unused?',
            'realm': self.default_realm,
            'api_key': '42'}
        for key, value in defaults.items():
            kwargs[key] = kwargs.get(key, value)
        return UserProfile.objects.create(email=email, **kwargs)

    def create_stream(self, **kwargs):
        # type: (**Any) -> Stream
        defaults = {'name': 'stream name',
                    'realm': self.default_realm,
                    'date_created': self.TIME_LAST_HOUR}
        for key, value in defaults.items():
            kwargs[key] = kwargs.get(key, value)
        return Stream.objects.create(**kwargs)

    def create_message(self, sender, recipient, **kwargs):
        # type: (UserProfile, Recipient, **Any) -> Message
        defaults = {
            'sender': sender,
            'recipient': recipient,
            'subject': 'subject',
            'content': 'hi',
            'pub_date': self.TIME_LAST_HOUR,
            'sending_client': get_client("website")}
        for key, value in defaults.items():
            kwargs[key] = kwargs.get(key, value)
        return Message.objects.create(**kwargs)

    # kwargs should only ever be a UserProfile or Stream.
    def assertCountEquals(self, table, property, value, subgroup=None, end_time=TIME_ZERO,
                          interval=CountStat.HOUR, realm=None, **kwargs):
        # type: (Type[BaseCount], Text, int, Optional[Text], datetime, str, Optional[Realm], **models.Model) -> None
        queryset = table.objects.filter(property=property, interval=interval, end_time=end_time) \
                                .filter(**kwargs)
        if table is not InstallationCount:
            if realm is None:
                realm = self.default_realm
            queryset = queryset.filter(realm=realm)
        if subgroup is not None:
            queryset = queryset.filter(subgroup=subgroup)
        self.assertEqual(queryset.values_list('value', flat=True)[0], value)

# Tests manangement commands, backfilling, adding new stats, etc
class TestUpdateAnalyticsCounts(AnalyticsTestCase):
    def test_analytics_stat_write(self):
        # type: () -> None
        # might change if we refactor count_query

        stat = CountStat('test_stat_write', zerver_count_stream_by_realm,
                         {'invite_only': False}, None, CountStat.HOUR, False)

        # add some stuff to zerver_*
        self.create_stream(name='stream1')
        self.create_stream(name='stream2')
        self.create_stream(name='stream3')

        # run do_pull_from_zerver
        do_fill_count_stat_at_hour(stat, self.TIME_ZERO)

        # check analytics_* values are correct
        self.assertCountEquals(RealmCount, 'test_stat_write', 3)

    def test_update_analytics_tables(self):
        # type: () -> None
        stat = CountStat('test_messages_sent', zerver_count_message_by_user, {}, None, CountStat.HOUR, False)

        user1 = self.create_user('email1')
        user2 = self.create_user('email2')
        recipient = Recipient.objects.create(type_id=user2.id, type=Recipient.PERSONAL)
        self.create_message(user1, recipient)

        # run command
        do_fill_count_stat_at_hour(stat, self.TIME_ZERO)
        usercount_row = UserCount.objects.filter(realm=self.default_realm, interval=CountStat.HOUR,
                                                 property='test_messages_sent').values_list(
            'value', flat=True)[0]
        assert (usercount_row == 1)

        # run command with date before message creation
        do_fill_count_stat_at_hour(stat, self.TIME_LAST_HOUR)

        # check no earlier rows created, old ones still there
        self.assertFalse(UserCount.objects.filter(end_time__lt = self.TIME_LAST_HOUR).exists())
        self.assertCountEquals(UserCount, 'test_messages_sent', 1, user = user1)

class TestProcessCountStat(AnalyticsTestCase):
    def make_dummy_count_stat(self, current_time):
        # type: (datetime) -> CountStat
        dummy_query = """INSERT INTO analytics_realmcount (realm_id, property, end_time, interval, value)
                                VALUES (1, 'test stat', '%(end_time)s','hour', 22)""" % {'end_time': current_time}
        count_stat = CountStat('test stat', ZerverCountQuery(Recipient, UserCount, dummy_query),
                               {}, None, CountStat.HOUR, False)
        return count_stat

    def assertFillStateEquals(self, end_time, state = FillState.DONE, property = None):
        # type: (datetime, int, Optional[Text]) -> None
        count_stat = self.make_dummy_count_stat(end_time)
        if property is None:
            property = count_stat.property
        fill_state = get_fill_state(property)
        self.assertEqual(fill_state['end_time'], end_time)
        self.assertEqual(fill_state['state'], state)

    def test_process_stat(self):
        # type: () -> None
        # process new stat
        current_time = installation_epoch() + self.HOUR
        count_stat = self.make_dummy_count_stat(current_time)
        process_count_stat(count_stat, current_time)
        self.assertFillStateEquals(current_time)
        self.assertEqual(InstallationCount.objects.filter(property = count_stat.property,
                                                          interval = CountStat.HOUR).count(), 1)

        # dirty stat
        FillState.objects.filter(property=count_stat.property).update(state=FillState.STARTED)
        process_count_stat(count_stat, current_time)
        self.assertFillStateEquals(current_time)
        self.assertEqual(InstallationCount.objects.filter(property = count_stat.property,
                                                          interval = CountStat.HOUR).count(), 1)

        # clean stat, no update
        process_count_stat(count_stat, current_time)
        self.assertFillStateEquals(current_time)
        self.assertEqual(InstallationCount.objects.filter(property = count_stat.property,
                                                          interval = CountStat.HOUR).count(), 1)

        # clean stat, with update
        current_time = current_time + self.HOUR
        count_stat = self.make_dummy_count_stat(current_time)
        process_count_stat(count_stat, current_time)
        self.assertFillStateEquals(current_time)
        self.assertEqual(InstallationCount.objects.filter(property = count_stat.property,
                                                          interval = CountStat.HOUR).count(), 2)

    # test users added in last hour
    def test_add_new_users(self):
        # type: () -> None
        stat = CountStat('add_new_user_test', zerver_count_user_by_realm, {}, None, CountStat.HOUR, False)

        # add new users to realm in last hour
        self.create_user('email1')
        self.create_user('email2')

        # add a new user before an hour
        self.create_user('email3', date_joined=self.TIME_ZERO - 2*self.HOUR)

        # check if user added before the hour is not included
        do_fill_count_stat_at_hour(stat, self.TIME_ZERO)
        # do_update is writing the stat.property to all zerver tables

        self.assertCountEquals(RealmCount, 'add_new_user_test', 2)

    def test_count_before_realm_creation(self):
        # type: () -> None
        stat = CountStat('test_active_humans', zerver_count_user_by_realm,
                         {'is_bot': False, 'is_active': True}, None, CountStat.HOUR, False)

        realm = Realm.objects.create(string_id='string_id', name='name', domain='domain',
                                     date_created=self.TIME_ZERO)
        self.create_user('email', realm=realm)

        # run count prior to realm creation
        do_fill_count_stat_at_hour(stat, self.TIME_LAST_HOUR)
        self.assertFalse(RealmCount.objects.filter(realm=realm).exists())

    def test_empty_counts_in_realm(self):
        # type: () -> None
        # test that rows with empty counts are returned if realm exists
        stat = CountStat('test_active_humans', zerver_count_user_by_realm,
                         {'is_bot': False, 'is_active': True}, None, CountStat.HOUR, False)
        do_fill_count_stat_at_hour(stat, self.TIME_ZERO)
        self.assertFalse(RealmCount.objects.filter(realm=self.default_realm).exists())

    def test_empty_message_aggregates(self):
        # type: () -> None
        # test that we write empty rows to realmcount in the event that we
        # have no messages and no users
        stat = COUNT_STATS['messages_sent']
        do_fill_count_stat_at_hour(stat, self.TIME_ZERO)
        self.assertFalse(RealmCount.objects.filter(realm=self.default_realm).exists())

class TestAggregates(AnalyticsTestCase):
    pass

class TestXByYQueries(AnalyticsTestCase):
    def test_message_to_stream_aggregation(self):
        # type: () -> None
        stat = CountStat('test_messages_to_stream', zerver_count_message_by_stream, {}, None, CountStat.HOUR, False)

        # write some messages
        user = self.create_user('email')
        stream = self.create_stream(date_created=self.TIME_ZERO - 2*self.HOUR)

        recipient = Recipient(type_id=stream.id, type=Recipient.STREAM)
        recipient.save()

        self.create_message(user, recipient = recipient)

        # run command
        do_fill_count_stat_at_hour(stat, self.TIME_ZERO)

        self.assertCountEquals(StreamCount, 'test_messages_to_stream', 1)

class TestCountStats(AnalyticsTestCase):
    def setUp(self):
        # type: () -> None
        super(TestCountStats, self).setUp()
        self.second_realm = Realm.objects.create(
            string_id='second-realm', name='Second Realm',
            domain='second.analytics', date_created=self.TIME_ZERO-2*self.DAY)
        user = self.create_user('user@second.analytics', realm=self.second_realm)
        stream = self.create_stream(realm=self.second_realm)
        recipient = Recipient.objects.create(type_id=stream.id, type=Recipient.STREAM)
        self.create_message(user, recipient)

        future_user = self.create_user('future_user@second.analytics', realm=self.second_realm,
                                       date_joined=self.TIME_ZERO)
        future_stream = self.create_stream(name='future stream', realm=self.second_realm,
                                           date_created=self.TIME_ZERO)
        future_recipient = Recipient.objects.create(type_id=future_stream.id, type=Recipient.STREAM)
        self.create_message(future_user, future_recipient, pub_date=self.TIME_ZERO)

    def test_active_users_by_is_bot(self):
        # type: () -> None
        property = 'active_users:is_bot'
        stat = COUNT_STATS[property]

        # To be included
        self.create_user('email1-bot', is_bot=True)
        self.create_user('email2-bot', is_bot=True, date_joined=self.TIME_ZERO-25*self.HOUR)
        self.create_user('email3-human', is_bot=False)

        # To be excluded
        self.create_user('email4', is_active=False)

        do_fill_count_stat_at_hour(stat, self.TIME_ZERO)

        self.assertCountEquals(RealmCount, property, 2, subgroup='true', interval=stat.interval)
        self.assertCountEquals(RealmCount, property, 1, subgroup='false', interval=stat.interval)
        self.assertCountEquals(RealmCount, property, 1, subgroup='false', interval=stat.interval, realm=self.second_realm)
        self.assertEqual(RealmCount.objects.count(), 3)
        self.assertFalse(UserCount.objects.exists())
        self.assertFalse(StreamCount.objects.exists())
