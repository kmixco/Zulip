from django.db.models import Count, Sum

from zerver.models import Realm, UserProfile, Message

from datetime import datetime, timedelta


# what is the scope of this?
ANALYTICS_INTERVALS = {'hour' : timedelta(seconds=3600), 'day' : timedelta(days=1), 'gauge' : None}

class AnalyticsInterval:
    def __init__(self, name, end = datetime.utcnow(), round_to_boundary = 'hour'):
        if round_to_boundary is not None:
            self.end = interval_boundary_floor(end, round_to_boundary)
        if name not in ANALYTICS_INTERVALS:
            raise ValueError('%s is not a valid analytics interval name' % name)
        self.name = name
        if name == 'gauge':
            self.start = datetime(year = datetime.MINYEAR)
        else:
            self.start = self.end - ANALYTICS_INTERVALS[name])
    # add way to init with start_time and end_time, and no interval

def interval_boundary_floor(datetime_object, interval_name):
    # type: (datetime, text_type) -> datetime
    # don't have to worry about leap seconds, since datetime doesn't support it
    # datetime objects are (year, month, day, hour, minutes, seconds, microseconds)
    if interval_name == 'hour':
        return datetime(*datetime_object.timetuple()[:4])
    elif interval_name == 'day':
        return datetime(*datetime_object.timetuple()[:3])
    else:
        raise ValueError("Unknown interval name", interval_name)

# will have to rewrite this once we have interval names like 'quarter', but
# seems fine for now
def compute_intervals(first, last, interval_name, frequency):
    current = interval_boundary_floor(last, interval_name)
    ans = []
    while current >= first:
        ans.append(AnalyticsInterval(interval_name, current, round_to_boundary = None))
        current -= ANALYTICS_INTERVALS[frequency]
    ans.reverse()
    return ans

# delete rest of below ..?
def interval_boundary_next(datetime_object, interval):
    # type: (datetime, text_type) -> datetime
    # don't have to worry about leap seconds, since datetime doesn't support it
    # datetime objects are (year, month, day, hour, minutes, seconds, microseconds)
    last = interval_boundary_floor(datetime_object, interval)
    if interval == 'hour':
        return last + timedelta(hour = 1)
    elif interval == 'day':
        return last + timedelta(day = 1)
    else:
        raise ValueError("Unknown interval", interval)

def interval_boundary_lastfloor(datetime_object, interval):
    # type: (datetime, text_type) -> datetime
    last = interval_boundary_floor(datetime_object, interval)
    return interval_boundary_lastfloor(last - timedelta(microseconds = 1), interval)

def interval_boundaries(datetime_object, interval):
    # type: (datetime, text_type) -> Tuple[datetime, datetime]
    if interval == 'hour':
        start = datetime(*datetime_object.timetuple()[:4])
        end = start + timedelta(hour = 1)
    elif interval == 'day':
        start = datetime(*datetime_object.timetuple()[:3])
        end = start + timedelta(day = 1)
    else:
        raise ValueError("Unknown interval", interval)
    return (start, end)

def prev_interval_boundaries(datetime_object, interval):
    # type: (datetime, text_type) -> Tuple[datetime, datetime]
    if interval == 'hour':
        end = datetime(*datetime_object.timetuple()[:4])
        start = end - timedelta(hour = 1)
    elif interval == 'day':
        end = datetime(*datetime_object.timetuple()[:3])
        start = end - timedelta(day = 1)
    else:
        raise ValueError("Unknown interval", interval)
    return (start, end)


##### put stuff into the analytics databases

def exists_row_with_values(table, **filter_args):
    return len(table.objects.filter(**filter_args)[:1]) > 0

def insert_count(table, valid_ids, rows, property, analytics_interval):
    table.objects.bulk_create([table(property = property,
                                     end_time = analytics_interval.end,
                                     interval = analytics_interval.name,
                                     **row)
                               for row in rows if row['id'] in valid_ids])

def insert_realmcount(realm_ids, realm_rows, property, analytics_interval):
    values = defaultdict(int)
    for row in realm_rows:
        values[row['realm']] = row['value']
    RealmCount.objects.bulk_create([RealmCount(realm_id = realm_id,
                                               property = property,
                                               value = values[realm_id],
                                               end_time = analytics_interval.end,
                                               interval = analytics_interval.name)
                                    for realm_id in realm_ids])

def process_realmcount(realm_ids, property, value_function, analytics_interval):
    if not exists_row_with_values(RealmCount,
                                  end_time = analytics_interval.end,
                                  interval = analytics_interval.name,
                                  property =  property):
        values = value_function(analytics_interval)
        insert_realmcount(realm_ids, values, property, analytics_interval)

def insert_usercount(user_ids, user_rows, property, analytics_interval):
    realm_values = defaultdict(int)
    for row in user_rows:
        realm_values[row['userprofile']] = (row['realm'], row['value'])
    UserCount.objects.bulk_create([UserCount(user_id = user_id
                                             realm_id = realm_values[user_id][0],
                                             property = property,
                                             value = realm_values[user_id][1],
                                             end_time = analytics_interval.end,
                                             interval = analytics_interval.name)
                                   for user_id in user_ids])

def process_usercount(user_ids, property, value_function, analytics_interval):
    if not exists_row_with_values(UserCount,
                                  end_time = analytics_interval.end,
                                  interval = analytics_interval.name,
                                  property =  property):
        rows = value_function(analytics_interval)
        insert_usercount(user_ids, rows, property, analytics_interval)




##### aggregators

def aggregate_user_to_realm(self, property, analytics_interval):
    return UserCount.objects \
            .filter(end_time = analytics_interval.end,
                    interval = analytics_interval.name,
                    property = property) \
            .values('realm') \
            .annotate(value=Sum('value'))

def aggregate_realm_hour_to_day(self, property, analytics_interval):
    return RealmCount.objects \
                     .filter(start_time__gt = analytics_interval.end - timedelta(day=1),
                             start_time__lte = analytics_interval.end,
                             property = property) \
                     .values('realm') \
                     .annotate(value=Sum('value'))


## methods that hit the prod databases directly

# day (utc?)
def get_active_user_count_by_realm(analytics_interval):
    return UserActivity.objects \
                       .filter(last_visit__gte = analytics_interval.start,
                               last_visit__lt = analytics_interval.end) \
                       pass

# gauge
def get_user_profile_count_by_realm(analytics_interval):
    return UserProfile.objects \
                      .filter(is_bot = False,
                              is_active = True,
                              date_joined__lt = analytics_interval.end) \
                      .values('realm') \
                      .annotate(value=Count('realm'))

# gauge
def get_bot_count_by_realm(analytics_interval):
    return UserProfile.objects \
                      .filter(is_bot = True,
                              is_active = True,
                              date_joined__lt = analytics_interval.end) \
                      .values('realm') \
                      .annotate(value=Count('realm'))

def get_message_counts_by_user(analytics_interval):
    return Message.objects \
                  .filter(pub_date__gte = analytics_interval.start,
                          pub_date__lt = analytics_interval.end) \
                  .values(userprofile='sender_id', realm='sender_id__realm') \
                  .annotate(value=Count('sender_id'))


def get_total_users_by_realm(self, gauge_time, interval):
    pass

def get_active_users_by_realm(self, start_time, interval):
    pass

def get_at_risk_count_by_realm(self, gauge_time):
    pass
