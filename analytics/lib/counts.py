from django.conf import settings
from django.db import connection, models
from django.db.models import F
from django.utils import timezone

from analytics.models import InstallationCount, RealmCount, \
    UserCount, StreamCount, BaseCount, FillState, Anomaly, installation_epoch
from zerver.models import Realm, UserProfile, Message, Stream, \
    UserActivityInterval, RealmAuditLog, models
from zerver.lib.timestamp import floor_to_day, floor_to_hour, ceiling_to_day, \
    ceiling_to_hour

from typing import Any, Callable, Dict, Optional, Text, Tuple, Type, Union

from collections import defaultdict
from datetime import timedelta, datetime
import logging
import time

## Logging setup ##
log_format = '%(asctime)s %(levelname)-8s %(message)s'
logging.basicConfig(format=log_format)

formatter = logging.Formatter(log_format)
file_handler = logging.FileHandler(settings.ANALYTICS_LOG_PATH)
file_handler.setFormatter(formatter)

logger = logging.getLogger("zulip.management")
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)

# You can't subtract timedelta.max from a datetime, so use this instead
TIMEDELTA_MAX = timedelta(days=365*1000)

class CountStat(object):
    HOUR = 'hour'
    DAY = 'day'
    FREQUENCIES = frozenset([HOUR, DAY])

    def __init__(self, property, data_collector, frequency, interval=None):
        # type: (str, DataCollector, str, Optional[timedelta]) -> None
        self.property = property
        self.data_collector = data_collector
        # might have to do something different for bitfields
        if frequency not in self.FREQUENCIES:
            raise AssertionError("Unknown frequency: %s" % (frequency,))
        self.frequency = frequency
        if interval is not None:
            self.interval = interval
        elif frequency == CountStat.HOUR:
            self.interval = timedelta(hours=1)
        else: # frequency == CountStat.DAY
            self.interval = timedelta(days=1)
        self.is_logging = False
        self.custom_pull_function = None # type: Optional[Callable[[CountStat, datetime, datetime], None]]

    def __unicode__(self):
        # type: () -> Text
        return u"<CountStat: %s>" % (self.property,)

class LoggingCountStat(CountStat):
    def __init__(self, property, output_table, frequency):
        # type: (str, Type[BaseCount], str) -> None
        CountStat.__init__(self, property, DataCollector(output_table, None, None), frequency)
        self.is_logging = True

class CustomPullCountStat(CountStat):
    def __init__(self, property, output_table, frequency, custom_pull_function):
        # type: (str, Type[BaseCount], str, Callable[[CountStat, datetime, datetime], None]) -> None
        CountStat.__init__(self, property, DataCollector(output_table, None, None), frequency)
        self.custom_pull_function = custom_pull_function

class DataCollector(object):
    def __init__(self, output_table, query, group_by):
        # type: (Type[BaseCount], Text, Optional[Tuple[models.Model, str]]) -> None
        self.output_table = output_table
        self.query = query
        self.group_by = group_by

def do_update_fill_state(fill_state, end_time, state):
    # type: (FillState, datetime, int) -> None
    fill_state.end_time = end_time
    fill_state.state = state
    fill_state.save()

def process_count_stat(stat, fill_to_time):
    # type: (CountStat, datetime) -> None
    fill_state = FillState.objects.filter(property=stat.property).first()
    if fill_state is None:
        currently_filled = installation_epoch()
        fill_state = FillState.objects.create(property=stat.property,
                                              end_time=currently_filled,
                                              state=FillState.DONE)
        logger.info("INITIALIZED %s %s" % (stat.property, currently_filled))
    elif fill_state.state == FillState.STARTED:
        logger.info("UNDO START %s %s" % (stat.property, fill_state.end_time))
        do_delete_counts_at_hour(stat, fill_state.end_time)
        currently_filled = fill_state.end_time - timedelta(hours = 1)
        do_update_fill_state(fill_state, currently_filled, FillState.DONE)
        logger.info("UNDO DONE %s" % (stat.property,))
    elif fill_state.state == FillState.DONE:
        currently_filled = fill_state.end_time
    else:
        raise AssertionError("Unknown value for FillState.state: %s." % (fill_state.state,))

    currently_filled = currently_filled + timedelta(hours = 1)
    while currently_filled <= fill_to_time:
        logger.info("START %s %s" % (stat.property, currently_filled))
        start = time.time()
        do_update_fill_state(fill_state, currently_filled, FillState.STARTED)
        do_fill_count_stat_at_hour(stat, currently_filled)
        do_update_fill_state(fill_state, currently_filled, FillState.DONE)
        end = time.time()
        currently_filled = currently_filled + timedelta(hours = 1)
        logger.info("DONE %s (%dms)" % (stat.property, (end-start)*1000))

# We assume end_time is on an hour boundary, and is timezone aware.
# It is the caller's responsibility to enforce this!
def do_fill_count_stat_at_hour(stat, end_time):
    # type: (CountStat, datetime) -> None
    if stat.frequency == CountStat.DAY and (end_time != floor_to_day(end_time)):
        return

    start_time = end_time - stat.interval
    if stat.custom_pull_function is not None:
        stat.custom_pull_function(stat, start_time, end_time)
    elif not stat.is_logging:
        do_pull_from_zerver(stat, start_time, end_time)
    do_aggregate_to_summary_table(stat, end_time)

def do_delete_counts_at_hour(stat, end_time):
    # type: (CountStat, datetime) -> None
    if stat.is_logging:
        InstallationCount.objects.filter(property=stat.property, end_time=end_time).delete()
        if stat.data_collector.output_table in [UserCount, StreamCount]:
            RealmCount.objects.filter(property=stat.property, end_time=end_time).delete()
    else:
        UserCount.objects.filter(property=stat.property, end_time=end_time).delete()
        StreamCount.objects.filter(property=stat.property, end_time=end_time).delete()
        RealmCount.objects.filter(property=stat.property, end_time=end_time).delete()
        InstallationCount.objects.filter(property=stat.property, end_time=end_time).delete()

def do_drop_all_analytics_tables():
    # type: () -> None
    UserCount.objects.all().delete()
    StreamCount.objects.all().delete()
    RealmCount.objects.all().delete()
    InstallationCount.objects.all().delete()
    FillState.objects.all().delete()
    Anomaly.objects.all().delete()

def do_aggregate_to_summary_table(stat, end_time):
    # type: (CountStat, datetime) -> None
    cursor = connection.cursor()

    # Aggregate into RealmCount
    output_table = stat.data_collector.output_table
    if output_table in (UserCount, StreamCount):
        realmcount_query = """
            INSERT INTO analytics_realmcount
                (realm_id, value, property, subgroup, end_time)
            SELECT
                zerver_realm.id, COALESCE(sum(%(output_table)s.value), 0), '%(property)s',
                %(output_table)s.subgroup, %%(end_time)s
            FROM zerver_realm
            JOIN %(output_table)s
            ON
                zerver_realm.id = %(output_table)s.realm_id
            WHERE
                %(output_table)s.property = '%(property)s' AND
                %(output_table)s.end_time = %%(end_time)s
            GROUP BY zerver_realm.id, %(output_table)s.subgroup
        """ % {'output_table': output_table._meta.db_table,
               'property': stat.property}
        start = time.time()
        cursor.execute(realmcount_query, {'end_time': end_time})
        end = time.time()
        logger.info("%s RealmCount aggregation (%dms/%sr)" % (stat.property, (end-start)*1000, cursor.rowcount))

    # Aggregate into InstallationCount
    installationcount_query = """
        INSERT INTO analytics_installationcount
            (value, property, subgroup, end_time)
        SELECT
            sum(value), '%(property)s', analytics_realmcount.subgroup, %%(end_time)s
        FROM analytics_realmcount
        WHERE
            property = '%(property)s' AND
            end_time = %%(end_time)s
        GROUP BY analytics_realmcount.subgroup
    """ % {'property': stat.property}
    start = time.time()
    cursor.execute(installationcount_query, {'end_time': end_time})
    end = time.time()
    logger.info("%s InstallationCount aggregation (%dms/%sr)" % (stat.property, (end-start)*1000, cursor.rowcount))
    cursor.close()

# This is the only method that hits the prod databases directly.
def do_pull_from_zerver(stat, start_time, end_time):
    # type: (CountStat, datetime, datetime) -> None
    group_by = stat.data_collector.group_by
    if group_by is None:
        subgroup = 'NULL'
        group_by_clause  = ''
    else:
        subgroup = '%s.%s' % (group_by[0]._meta.db_table, group_by[1])
        group_by_clause = ', ' + subgroup

    # We do string replacement here because passing group_by_clause as a param
    # may result in problems when running cursor.execute; we do
    # the string formatting prior so that cursor.execute runs it as sql
    query_ = stat.data_collector.query % {'property': stat.property,
                                          'subgroup': subgroup,
                                          'group_by_clause': group_by_clause}
    cursor = connection.cursor()
    start = time.time()
    cursor.execute(query_, {'time_start': start_time, 'time_end': end_time})
    end = time.time()
    logger.info("%s do_pull_from_zerver (%dms/%sr)" % (stat.property, (end-start)*1000, cursor.rowcount))
    cursor.close()

# called from zerver/lib/actions.py; should not throw any errors
def do_increment_logging_stat(zerver_object, stat, subgroup, event_time, increment=1):
    # type: (Union[Realm, UserProfile, Stream], CountStat, Optional[Union[str, int, bool]], datetime, int) -> None
    table = stat.data_collector.output_table
    if table == RealmCount:
        id_args = {'realm': zerver_object}
    elif table == UserCount:
        id_args = {'realm': zerver_object.realm, 'user': zerver_object}
    else: # StreamCount
        id_args = {'realm': zerver_object.realm, 'stream': zerver_object}

    if stat.frequency == CountStat.DAY:
        end_time = ceiling_to_day(event_time)
    else: # CountStat.HOUR:
        end_time = ceiling_to_hour(event_time)

    row, created = table.objects.get_or_create(
        property=stat.property, subgroup=subgroup, end_time=end_time,
        defaults={'value': increment}, **id_args)
    if not created:
        row.value = F('value') + increment
        row.save(update_fields=['value'])

# Hardcodes the query needed by active_users:is_bot:day, since that is
# currently the only stat that uses this.
count_user_by_realm_query = """
    INSERT INTO analytics_realmcount
        (realm_id, value, property, subgroup, end_time)
    SELECT
        zerver_realm.id, count(*),'%(property)s', %(subgroup)s, %%(time_end)s
    FROM zerver_realm
    JOIN zerver_userprofile
    ON
        zerver_realm.id = zerver_userprofile.realm_id
    WHERE
        zerver_realm.date_created < %%(time_end)s AND
        zerver_userprofile.date_joined >= %%(time_start)s AND
        zerver_userprofile.date_joined < %%(time_end)s AND
        zerver_userprofile.is_active = TRUE
    GROUP BY zerver_realm.id %(group_by_clause)s
"""
zerver_count_user_by_realm = DataCollector(RealmCount, count_user_by_realm_query,
                                           (UserProfile, 'is_bot'))

# currently .sender_id is only Message specific thing
count_message_by_user_query = """
    INSERT INTO analytics_usercount
        (user_id, realm_id, value, property, subgroup, end_time)
    SELECT
        zerver_userprofile.id, zerver_userprofile.realm_id, count(*), '%(property)s', %(subgroup)s, %%(time_end)s
    FROM zerver_userprofile
    JOIN zerver_message
    ON
        zerver_userprofile.id = zerver_message.sender_id
    WHERE
        zerver_userprofile.date_joined < %%(time_end)s AND
        zerver_message.pub_date >= %%(time_start)s AND
        zerver_message.pub_date < %%(time_end)s
    GROUP BY zerver_userprofile.id %(group_by_clause)s
"""
zerver_count_message_by_user_is_bot = DataCollector(UserCount, count_message_by_user_query,
                                                    (UserProfile, 'is_bot'))
zerver_count_message_by_user_client = DataCollector(UserCount, count_message_by_user_query,
                                                    (Message, 'sending_client_id'))

# Currently unused and untested
count_stream_by_realm_query = """
    INSERT INTO analytics_realmcount
        (realm_id, value, property, subgroup, end_time)
    SELECT
        zerver_realm.id, count(*), '%(property)s', %(subgroup)s, %%(time_end)s
    FROM zerver_realm
    JOIN zerver_stream
    ON
        zerver_realm.id = zerver_stream.realm_id AND
    WHERE
        zerver_realm.date_created < %%(time_end)s AND
        zerver_stream.date_created >= %%(time_start)s AND
        zerver_stream.date_created < %%(time_end)s
    GROUP BY zerver_realm.id %(group_by_clause)s
"""
zerver_count_stream_by_realm = DataCollector(RealmCount, count_stream_by_realm_query, None)

# This query violates the count_X_by_Y_query conventions in several ways. One,
# the X table is not specified by the query name; MessageType is not a zerver
# table. Two, it ignores the subgroup column in the CountStat object; instead,
# it uses 'message_type' from the subquery to fill in the subgroup column.
count_message_type_by_user_query = """
    INSERT INTO analytics_usercount
            (realm_id, user_id, value, property, subgroup, end_time)
    SELECT realm_id, id, SUM(count) AS value, '%(property)s', message_type, %%(time_end)s
    FROM
    (
        SELECT zerver_userprofile.realm_id, zerver_userprofile.id, count(*),
        CASE WHEN
                  zerver_recipient.type = 1 THEN 'private_message'
             WHEN
                  zerver_recipient.type = 3 THEN 'huddle_message'
             WHEN
                  zerver_stream.invite_only = TRUE THEN 'private_stream'
             ELSE 'public_stream'
        END
        message_type

        FROM zerver_userprofile
        JOIN zerver_message
        ON
            zerver_userprofile.id = zerver_message.sender_id AND
            zerver_message.pub_date >= %%(time_start)s AND
            zerver_message.pub_date < %%(time_end)s
        JOIN zerver_recipient
        ON
            zerver_message.recipient_id = zerver_recipient.id
        LEFT JOIN zerver_stream
        ON
            zerver_recipient.type_id = zerver_stream.id
        GROUP BY zerver_userprofile.realm_id, zerver_userprofile.id, zerver_recipient.type, zerver_stream.invite_only
    ) AS subquery
    GROUP BY realm_id, id, message_type
"""
zerver_count_message_type_by_user = DataCollector(UserCount, count_message_type_by_user_query, None)

# Note that this query also joins to the UserProfile table, since all
# current queries that use this also subgroup on UserProfile.is_bot. If in
# the future there is a query that counts messages by stream and doesn't need
# the UserProfile table, consider writing a new query for efficiency.
count_message_by_stream_query = """
    INSERT INTO analytics_streamcount
        (stream_id, realm_id, value, property, subgroup, end_time)
    SELECT
        zerver_stream.id, zerver_stream.realm_id, count(*), '%(property)s', %(subgroup)s, %%(time_end)s
    FROM zerver_stream
    JOIN zerver_recipient
    ON
        zerver_stream.id = zerver_recipient.type_id
    JOIN zerver_message
    ON
        zerver_recipient.id = zerver_message.recipient_id
    JOIN zerver_userprofile
    ON
        zerver_message.sender_id = zerver_userprofile.id
    WHERE
        zerver_stream.date_created < %%(time_end)s AND
        zerver_recipient.type = 2 AND
        zerver_message.pub_date >= %%(time_start)s AND
        zerver_message.pub_date < %%(time_end)s
    GROUP BY zerver_stream.id %(group_by_clause)s
"""
zerver_count_message_by_stream = DataCollector(StreamCount, count_message_by_stream_query,
                                               (UserProfile, 'is_bot'))

check_useractivityinterval_by_user_query = """
    INSERT INTO analytics_usercount
        (user_id, realm_id, value, property, subgroup, end_time)
    SELECT
        zerver_userprofile.id, zerver_userprofile.realm_id, 1, '%(property)s', %(subgroup)s, %%(time_end)s
    FROM zerver_userprofile
    JOIN zerver_useractivityinterval
    ON
        zerver_userprofile.id = zerver_useractivityinterval.user_profile_id
    WHERE
        zerver_useractivityinterval.end >= %%(time_start)s AND
        zerver_useractivityinterval.start < %%(time_end)s
    GROUP BY zerver_userprofile.id %(group_by_clause)s
"""
zerver_check_useractivityinterval_by_user = DataCollector(
    UserCount, check_useractivityinterval_by_user_query, None)

# Currently hardcodes the query needed for active_users_audit:is_bot:day.
# Assumes that a user cannot have two RealmAuditLog entries with the same event_time and
# event_type in ['user_created', 'user_deactivated', etc].
# In particular, it's important to ensure that migrations don't cause that to happen.
check_realmauditlog_by_user_query = """
    INSERT INTO analytics_usercount
        (user_id, realm_id, value, property, subgroup, end_time)
    SELECT
        ral1.modified_user_id, ral1.realm_id, 1, '%(property)s', %(subgroup)s, %%(time_end)s
    FROM zerver_realmauditlog ral1
    JOIN (
        SELECT modified_user_id, max(event_time) AS max_event_time
        FROM zerver_realmauditlog
        WHERE
            event_type in ('user_created', 'user_deactivated', 'user_activated', 'user_reactivated') AND
            event_time < %%(time_end)s
        GROUP BY modified_user_id
    ) ral2
    ON
        ral1.event_time = max_event_time AND
        ral1.modified_user_id = ral2.modified_user_id
    JOIN zerver_userprofile
    ON
        ral1.modified_user_id = zerver_userprofile.id
    WHERE
        ral1.event_type in ('user_created', 'user_activated', 'user_reactivated')
"""
zerver_check_realmauditlog_by_user = DataCollector(UserCount, check_realmauditlog_by_user_query,
                                                   (UserProfile, 'is_bot'))

def do_pull_minutes_active(stat, start_time, end_time):
    # type: (CountStat, datetime, datetime) -> None
    timer_start = time.time()
    user_activity_intervals = UserActivityInterval.objects.filter(
        end__gt=start_time, start__lt=end_time
    ).select_related(
        'user_profile'
    ).values_list(
        'user_profile_id', 'user_profile__realm_id', 'start', 'end')

    seconds_active = defaultdict(float) # type: Dict[Tuple[int, int], float]
    for user_id, realm_id, interval_start, interval_end in user_activity_intervals:
        start = max(start_time, interval_start)
        end = min(end_time, interval_end)
        seconds_active[(user_id, realm_id)] += (end - start).total_seconds()

    rows = [UserCount(user_id=ids[0], realm_id=ids[1], property=stat.property,
                      end_time=end_time, value=int(seconds // 60))
            for ids, seconds in seconds_active.items() if seconds >= 60]
    UserCount.objects.bulk_create(rows)

    logger.info("%s do_pull_minutes_active (%dms/%sr)" %
                (stat.property, (time.time()-timer_start)*1000, len(rows)))

count_stats_ = [
    CountStat('messages_sent:is_bot:hour', zerver_count_message_by_user_is_bot, CountStat.HOUR),
    CountStat('messages_sent:message_type:day', zerver_count_message_type_by_user, CountStat.DAY),
    CountStat('messages_sent:client:day', zerver_count_message_by_user_client, CountStat.DAY),
    CountStat('messages_in_stream:is_bot:day', zerver_count_message_by_stream, CountStat.DAY),

    # Sanity check on the bottom two stats. Is only an approximation,
    # e.g. if a user is deactivated between the end of the day and when this
    # stat is run, they won't be counted.
    CountStat('active_users:is_bot:day', zerver_count_user_by_realm,
              CountStat.DAY, interval=TIMEDELTA_MAX),
    # In RealmCount, 'active_humans_audit::day' should be the partial sum sequence
    # of 'active_users_log:is_bot:day', for any realm that started after the
    # latter stat was introduced.
    # 'active_users_audit:is_bot:day' is the canonical record of which users were
    # active on which days (in the UserProfile.is_active sense).
    CountStat('active_users_audit:is_bot:day', zerver_check_realmauditlog_by_user, CountStat.DAY),
    LoggingCountStat('active_users_log:is_bot:day', RealmCount, CountStat.DAY),

    # The minutes=15 part is due to the 15 minutes added in
    # zerver.lib.actions.do_update_user_activity_interval.
    CountStat('15day_actives::day', zerver_check_useractivityinterval_by_user,
              CountStat.DAY, interval=timedelta(days=15)-timedelta(minutes=15)),
    CustomPullCountStat('minutes_active::day', UserCount, CountStat.DAY, do_pull_minutes_active)
]

COUNT_STATS = {stat.property: stat for stat in count_stats_}
