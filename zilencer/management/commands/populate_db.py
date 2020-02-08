import itertools
import os
import random
from typing import Any, Callable, Dict, List, \
    Mapping, Sequence, Tuple

import ujson
from datetime import datetime
from django.conf import settings
from django.contrib.sessions.models import Session
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandParser
from django.db.models import F, Max
from django.utils.timezone import now as timezone_now
from django.utils.timezone import timedelta as timezone_timedelta
import pylibmc

from zerver.lib.actions import STREAM_ASSIGNMENT_COLORS, check_add_realm_emoji, \
    do_change_is_admin, do_send_messages, do_update_user_custom_profile_data_if_changed, \
    try_add_realm_custom_profile_field, try_add_realm_default_custom_profile_field
from zerver.lib.bulk_create import bulk_create_streams
from zerver.lib.cache import cache_set
from zerver.lib.generate_test_data import create_test_data
from zerver.lib.onboarding import create_if_missing_realm_internal_bots
from zerver.lib.push_notifications import logger as push_notifications_logger
from zerver.lib.server_initialization import create_internal_realm, create_users
from zerver.lib.storage import static_path
from zerver.lib.users import add_service
from zerver.lib.url_preview.preview import CACHE_NAME as PREVIEW_CACHE_NAME
from zerver.lib.user_groups import create_user_group
from zerver.lib.utils import generate_api_key
from zerver.models import CustomProfileField, DefaultStream, Message, Realm, RealmAuditLog, \
    RealmDomain, Recipient, Service, Stream, Subscription, \
    UserMessage, UserPresence, UserProfile, Huddle, Client, \
    get_client, get_huddle, get_realm, get_stream, \
    get_user, get_user_profile_by_id
from zerver.lib.types import ProfileFieldData

from scripts.lib.zulip_tools import get_or_create_dev_uuid_var_path

settings.TORNADO_SERVER = None
# Disable using memcached caches to avoid 'unsupported pickle
# protocol' errors if `populate_db` is run with a different Python
# from `run-dev.py`.
default_cache = settings.CACHES['default']
settings.CACHES['default'] = {
    'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'
}

def clear_database() -> None:
    # Hacky function only for use inside populate_db.  Designed to
    # allow running populate_db repeatedly in series to work without
    # flushing memcached or clearing the database manually.

    # With `zproject.test_settings`, we aren't using real memcached
    # and; we only need to flush memcached if we're populating a
    # database that would be used with it (i.e. zproject.dev_settings).
    if default_cache['BACKEND'] == 'django_pylibmc.memcached.PyLibMCCache':
        pylibmc.Client(
            [default_cache['LOCATION']],
            binary=True,
            username=default_cache["USERNAME"],
            password=default_cache["PASSWORD"],
            behaviors=default_cache["OPTIONS"],
        ).flush_all()

    model = None  # type: Any # Hack because mypy doesn't know these are model classes
    for model in [Message, Stream, UserProfile, Recipient,
                  Realm, Subscription, Huddle, UserMessage, Client,
                  DefaultStream]:
        model.objects.all().delete()
    Session.objects.all().delete()

# Suppress spammy output from the push notifications logger
push_notifications_logger.disabled = True

def subscribe_users_to_streams(realm: Realm, stream_dict: Dict[str, Dict[str, Any]]) -> None:
    subscriptions_to_add = []
    event_time = timezone_now()
    all_subscription_logs = []
    profiles = UserProfile.objects.select_related().filter(realm=realm)
    for i, stream_name in enumerate(stream_dict):
        stream = Stream.objects.get(name=stream_name, realm=realm)
        recipient = Recipient.objects.get(type=Recipient.STREAM, type_id=stream.id)
        for profile in profiles:
            # Subscribe to some streams.
            s = Subscription(
                recipient=recipient,
                user_profile=profile,
                color=STREAM_ASSIGNMENT_COLORS[i % len(STREAM_ASSIGNMENT_COLORS)])
            subscriptions_to_add.append(s)

            log = RealmAuditLog(realm=profile.realm,
                                modified_user=profile,
                                modified_stream=stream,
                                event_last_message_id=0,
                                event_type=RealmAuditLog.SUBSCRIPTION_CREATED,
                                event_time=event_time)
            all_subscription_logs.append(log)
    Subscription.objects.bulk_create(subscriptions_to_add)
    RealmAuditLog.objects.bulk_create(all_subscription_logs)

class Command(BaseCommand):
    help = "Populate a test database"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument('-n', '--num-messages',
                            dest='num_messages',
                            type=int,
                            default=500,
                            help='The number of messages to create.')

        parser.add_argument('-b', '--batch-size',
                            dest='batch_size',
                            type=int,
                            default=1000,
                            help='How many messages to process in a single batch')

        parser.add_argument('--extra-users',
                            dest='extra_users',
                            type=int,
                            default=0,
                            help='The number of extra users to create')

        parser.add_argument('--extra-bots',
                            dest='extra_bots',
                            type=int,
                            default=0,
                            help='The number of extra bots to create')

        parser.add_argument('--extra-streams',
                            dest='extra_streams',
                            type=int,
                            default=0,
                            help='The number of extra streams to create')

        parser.add_argument('--huddles',
                            dest='num_huddles',
                            type=int,
                            default=3,
                            help='The number of huddles to create.')

        parser.add_argument('--personals',
                            dest='num_personals',
                            type=int,
                            default=6,
                            help='The number of personal pairs to create.')

        parser.add_argument('--threads',
                            dest='threads',
                            type=int,
                            default=1,
                            help='The number of threads to use.')

        parser.add_argument('--percent-huddles',
                            dest='percent_huddles',
                            type=float,
                            default=15,
                            help='The percent of messages to be huddles.')

        parser.add_argument('--percent-personals',
                            dest='percent_personals',
                            type=float,
                            default=15,
                            help='The percent of messages to be personals.')

        parser.add_argument('--stickyness',
                            dest='stickyness',
                            type=float,
                            default=20,
                            help='The percent of messages to repeat recent folks.')

        parser.add_argument('--nodelete',
                            action="store_false",
                            default=True,
                            dest='delete',
                            help='Whether to delete all the existing messages.')

        parser.add_argument('--test-suite',
                            default=False,
                            action="store_true",
                            help='Configures populate_db to create a deterministic '
                            'data set for the backend tests.')

    def handle(self, **options: Any) -> None:
        if options["percent_huddles"] + options["percent_personals"] > 100:
            self.stderr.write("Error!  More than 100% of messages allocated.\n")
            return

        # Get consistent data for backend tests.
        if options["test_suite"]:
            random.seed(0)

        if options["delete"]:
            # Start by clearing all the data in our database
            clear_database()

            # Create our three default realms
            # Could in theory be done via zerver.lib.actions.do_create_realm, but
            # welcome-bot (needed for do_create_realm) hasn't been created yet
            create_internal_realm()
            zulip_realm = Realm.objects.create(
                string_id="zulip", name="Zulip Dev", emails_restricted_to_domains=True,
                description="The Zulip development environment default organization."
                            "  It's great for testing!",
                invite_required=False, org_type=Realm.CORPORATE)
            RealmDomain.objects.create(realm=zulip_realm, domain="zulip.com")
            if options["test_suite"]:
                mit_realm = Realm.objects.create(
                    string_id="zephyr", name="MIT", emails_restricted_to_domains=True,
                    invite_required=False, org_type=Realm.CORPORATE)
                RealmDomain.objects.create(realm=mit_realm, domain="mit.edu")

                lear_realm = Realm.objects.create(
                    string_id="lear", name="Lear & Co.", emails_restricted_to_domains=False,
                    invite_required=False, org_type=Realm.CORPORATE)

            # Create test Users (UserProfiles are automatically created,
            # as are subscriptions to the ability to receive personals).
            names = [
                ("Zoe", "ZOE@zulip.com"),
                ("Othello, the Moor of Venice", "othello@zulip.com"),
                ("Iago", "iago@zulip.com"),
                ("Prospero from The Tempest", "prospero@zulip.com"),
                ("Cordelia Lear", "cordelia@zulip.com"),
                ("King Hamlet", "hamlet@zulip.com"),
                ("aaron", "AARON@zulip.com"),
                ("Polonius", "polonius@zulip.com"),
            ]

            # For testing really large batches:
            # Create extra users with semi realistic names to make search
            # functions somewhat realistic.  We'll still create 1000 users
            # like Extra222 User for some predicability.
            num_names = options['extra_users']
            num_boring_names = 1000

            for i in range(min(num_names, num_boring_names)):
                full_name = 'Extra%03d User' % (i,)
                names.append((full_name, 'extrauser%d@zulip.com' % (i,)))

            if num_names > num_boring_names:
                fnames = ['Amber', 'Arpita', 'Bob', 'Cindy', 'Daniela', 'Dan', 'Dinesh',
                          'Faye', 'François', 'George', 'Hank', 'Irene',
                          'James', 'Janice', 'Jenny', 'Jill', 'John',
                          'Kate', 'Katelyn', 'Kobe', 'Lexi', 'Manish', 'Mark', 'Matt', 'Mayna',
                          'Michael', 'Pete', 'Peter', 'Phil', 'Phillipa', 'Preston',
                          'Sally', 'Scott', 'Sandra', 'Steve', 'Stephanie',
                          'Vera']
                mnames = ['de', 'van', 'von', 'Shaw', 'T.']
                lnames = ['Adams', 'Agarwal', 'Beal', 'Benson', 'Bonita', 'Davis',
                          'George', 'Harden', 'James', 'Jones', 'Johnson', 'Jordan',
                          'Lee', 'Leonard', 'Singh', 'Smith', 'Patel', 'Towns', 'Wall']

            for i in range(num_boring_names, num_names):
                fname = random.choice(fnames) + str(i)
                full_name = fname
                if random.random() < 0.7:
                    if random.random() < 0.5:
                        full_name += ' ' + random.choice(mnames)
                    full_name += ' ' + random.choice(lnames)
                email = fname.lower() + '@zulip.com'
                names.append((full_name, email))

            create_users(zulip_realm, names, tos_version=settings.TOS_VERSION)

            iago = get_user("iago@zulip.com", zulip_realm)
            do_change_is_admin(iago, True)
            iago.is_staff = True
            iago.save(update_fields=['is_staff'])

            guest_user = get_user("polonius@zulip.com", zulip_realm)
            guest_user.role = UserProfile.ROLE_GUEST
            guest_user.save(update_fields=['role'])

            # These bots are directly referenced from code and thus
            # are needed for the test suite.
            zulip_realm_bots = [
                ("Zulip Error Bot", "error-bot@zulip.com"),
                ("Zulip Default Bot", "default-bot@zulip.com"),
            ]
            for i in range(options["extra_bots"]):
                zulip_realm_bots.append(('Extra Bot %d' % (i,), 'extrabot%d@zulip.com' % (i,)))

            create_users(zulip_realm, zulip_realm_bots, bot_type=UserProfile.DEFAULT_BOT)

            zoe = get_user("zoe@zulip.com", zulip_realm)
            zulip_webhook_bots = [
                ("Zulip Webhook Bot", "webhook-bot@zulip.com"),
            ]
            # If a stream is not supplied in the webhook URL, the webhook
            # will (in some cases) send the notification as a PM to the
            # owner of the webhook bot, so bot_owner can't be None
            create_users(zulip_realm, zulip_webhook_bots,
                         bot_type=UserProfile.INCOMING_WEBHOOK_BOT, bot_owner=zoe)
            aaron = get_user("AARON@zulip.com", zulip_realm)

            zulip_outgoing_bots = [
                ("Outgoing Webhook", "outgoing-webhook@zulip.com")
            ]
            create_users(zulip_realm, zulip_outgoing_bots,
                         bot_type=UserProfile.OUTGOING_WEBHOOK_BOT, bot_owner=aaron)
            outgoing_webhook = get_user("outgoing-webhook@zulip.com", zulip_realm)
            add_service("outgoing-webhook", user_profile=outgoing_webhook, interface=Service.GENERIC,
                        base_url="http://127.0.0.1:5002", token=generate_api_key())

            # Add the realm internl bots to each realm.
            create_if_missing_realm_internal_bots()

            # Create public streams.
            stream_list = ["Verona", "Denmark", "Scotland", "Venice", "Rome"]
            stream_dict = {
                "Verona": {"description": "A city in Italy"},
                "Denmark": {"description": "A Scandinavian country"},
                "Scotland": {"description": "Located in the United Kingdom"},
                "Venice": {"description": "A northeastern Italian city"},
                "Rome": {"description": "Yet another Italian city", "is_web_public": True}
            }  # type: Dict[str, Dict[str, Any]]

            bulk_create_streams(zulip_realm, stream_dict)
            recipient_streams = [Stream.objects.get(name=name, realm=zulip_realm).id
                                 for name in stream_list]  # type: List[int]

            # Create subscriptions to streams.  The following
            # algorithm will give each of the users a different but
            # deterministic subset of the streams (given a fixed list
            # of users). For the test suite, we have a fixed list of
            # subscriptions to make sure test data is consistent
            # across platforms.

            subscriptions_list = []  # type: List[Tuple[UserProfile, Recipient]]
            profiles = UserProfile.objects.select_related().filter(
                is_bot=False).order_by("email")  # type: Sequence[UserProfile]

            if options["test_suite"]:
                subscriptions_map = {
                    'AARON@zulip.com': ['Verona'],
                    'cordelia@zulip.com': ['Verona'],
                    'hamlet@zulip.com': ['Verona', 'Denmark'],
                    'iago@zulip.com': ['Verona', 'Denmark', 'Scotland'],
                    'othello@zulip.com': ['Verona', 'Denmark', 'Scotland'],
                    'prospero@zulip.com': ['Verona', 'Denmark', 'Scotland', 'Venice'],
                    'ZOE@zulip.com': ['Verona', 'Denmark', 'Scotland', 'Venice', 'Rome'],
                    'polonius@zulip.com': ['Verona'],
                }

                for profile in profiles:
                    if profile.email not in subscriptions_map:
                        raise Exception('Subscriptions not listed for user %s' % (profile.email,))

                    for stream_name in subscriptions_map[profile.email]:
                        stream = Stream.objects.get(name=stream_name)
                        r = Recipient.objects.get(type=Recipient.STREAM, type_id=stream.id)
                        subscriptions_list.append((profile, r))
            else:
                num_streams = len(recipient_streams)
                num_users = len(profiles)
                for i, profile in enumerate(profiles):
                    # Subscribe to some streams.
                    fraction = float(i) / num_users
                    num_recips = int(num_streams * fraction) + 1

                    for type_id in recipient_streams[:num_recips]:
                        r = Recipient.objects.get(type=Recipient.STREAM, type_id=type_id)
                        subscriptions_list.append((profile, r))

            subscriptions_to_add = []  # type: List[Subscription]
            event_time = timezone_now()
            all_subscription_logs = []  # type: (List[RealmAuditLog])

            i = 0
            for profile, recipient in subscriptions_list:
                i += 1
                color = STREAM_ASSIGNMENT_COLORS[i % len(STREAM_ASSIGNMENT_COLORS)]
                s = Subscription(
                    recipient=recipient,
                    user_profile=profile,
                    color=color)

                subscriptions_to_add.append(s)

                log = RealmAuditLog(realm=profile.realm,
                                    modified_user=profile,
                                    modified_stream_id=recipient.type_id,
                                    event_last_message_id=0,
                                    event_type=RealmAuditLog.SUBSCRIPTION_CREATED,
                                    event_time=event_time)
                all_subscription_logs.append(log)

            Subscription.objects.bulk_create(subscriptions_to_add)
            RealmAuditLog.objects.bulk_create(all_subscription_logs)

            # Create custom profile field data
            phone_number = try_add_realm_custom_profile_field(zulip_realm, "Phone number",
                                                              CustomProfileField.SHORT_TEXT,
                                                              hint='')
            biography = try_add_realm_custom_profile_field(zulip_realm, "Biography",
                                                           CustomProfileField.LONG_TEXT,
                                                           hint='What are you known for?')
            favorite_food = try_add_realm_custom_profile_field(zulip_realm, "Favorite food",
                                                               CustomProfileField.SHORT_TEXT,
                                                               hint="Or drink, if you'd prefer")
            field_data = {
                'vim': {'text': 'Vim', 'order': '1'},
                'emacs': {'text': 'Emacs', 'order': '2'},
            }  # type: ProfileFieldData
            favorite_editor = try_add_realm_custom_profile_field(zulip_realm,
                                                                 "Favorite editor",
                                                                 CustomProfileField.CHOICE,
                                                                 field_data=field_data)
            birthday = try_add_realm_custom_profile_field(zulip_realm, "Birthday",
                                                          CustomProfileField.DATE)
            favorite_website = try_add_realm_custom_profile_field(zulip_realm, "Favorite website",
                                                                  CustomProfileField.URL,
                                                                  hint="Or your personal blog's URL")
            mentor = try_add_realm_custom_profile_field(zulip_realm, "Mentor",
                                                        CustomProfileField.USER)
            github_profile = try_add_realm_default_custom_profile_field(zulip_realm, "github")

            # Fill in values for Iago and Hamlet
            hamlet = get_user("hamlet@zulip.com", zulip_realm)
            do_update_user_custom_profile_data_if_changed(iago, [
                {"id": phone_number.id, "value": "+1-234-567-8901"},
                {"id": biography.id, "value": "Betrayer of Othello."},
                {"id": favorite_food.id, "value": "Apples"},
                {"id": favorite_editor.id, "value": "emacs"},
                {"id": birthday.id, "value": "2000-1-1"},
                {"id": favorite_website.id, "value": "https://zulip.readthedocs.io/en/latest/"},
                {"id": mentor.id, "value": [hamlet.id]},
                {"id": github_profile.id, "value": 'zulip'},
            ])
            do_update_user_custom_profile_data_if_changed(hamlet, [
                {"id": phone_number.id, "value": "+0-11-23-456-7890"},
                {
                    "id": biography.id,
                    "value": "I am:\n* The prince of Denmark\n* Nephew to the usurping Claudius",
                },
                {"id": favorite_food.id, "value": "Dark chocolate"},
                {"id": favorite_editor.id, "value": "vim"},
                {"id": birthday.id, "value": "1900-1-1"},
                {"id": favorite_website.id, "value": "https://blog.zulig.org"},
                {"id": mentor.id, "value": [iago.id]},
                {"id": github_profile.id, "value": 'zulipbot'},
            ])
        else:
            zulip_realm = get_realm("zulip")
            recipient_streams = [klass.type_id for klass in
                                 Recipient.objects.filter(type=Recipient.STREAM)]

        # Extract a list of all users
        user_profiles = list(UserProfile.objects.filter(is_bot=False))  # type: List[UserProfile]

        # Create a test realm emoji.
        IMAGE_FILE_PATH = static_path('images/test-images/checkbox.png')
        with open(IMAGE_FILE_PATH, 'rb') as fp:
            check_add_realm_emoji(zulip_realm, 'green_tick', iago, fp)

        if not options["test_suite"]:
            # Populate users with some bar data
            for user in user_profiles:
                status = UserPresence.ACTIVE  # type: int
                date = timezone_now()
                client = get_client("website")
                if user.full_name[0] <= 'H':
                    client = get_client("ZulipAndroid")
                UserPresence.objects.get_or_create(user_profile=user,
                                                   realm_id=user.realm_id,
                                                   client=client,
                                                   timestamp=date,
                                                   status=status)

        user_profiles_ids = [user_profile.id for user_profile in user_profiles]

        # Create several initial huddles
        for i in range(options["num_huddles"]):
            get_huddle(random.sample(user_profiles_ids, random.randint(3, 4)))

        # Create several initial pairs for personals
        personals_pairs = [random.sample(user_profiles_ids, 2)
                           for i in range(options["num_personals"])]

        # Generate a new set of test data.
        create_test_data()

        # prepopulate the URL preview/embed data for the links present
        # in the config.generate_data.json data set.  This makes it
        # possible for populate_db to run happily without Internet
        # access.
        with open("zerver/tests/fixtures/docs_url_preview_data.json", "r") as f:
            urls_with_preview_data = ujson.load(f)
            for url in urls_with_preview_data:
                cache_set(url, urls_with_preview_data[url], PREVIEW_CACHE_NAME)

        threads = options["threads"]
        jobs = []  # type: List[Tuple[int, List[List[int]], Dict[str, Any], Callable[[str], int], int]]
        for i in range(threads):
            count = options["num_messages"] // threads
            if i < options["num_messages"] % threads:
                count += 1
            jobs.append((count, personals_pairs, options, self.stdout.write, random.randint(0, 10**10)))

        for job in jobs:
            generate_and_send_messages(job)

        if options["delete"]:
            if options["test_suite"]:
                # Create test users; the MIT ones are needed to test
                # the Zephyr mirroring codepaths.
                testsuite_mit_users = [
                    ("Fred Sipb (MIT)", "sipbtest@mit.edu"),
                    ("Athena Consulting Exchange User (MIT)", "starnine@mit.edu"),
                    ("Esp Classroom (MIT)", "espuser@mit.edu"),
                ]
                create_users(mit_realm, testsuite_mit_users, tos_version=settings.TOS_VERSION)

                testsuite_lear_users = [
                    ("King Lear", "king@lear.org"),
                    ("Cordelia Lear", "cordelia@zulip.com"),
                ]
                create_users(lear_realm, testsuite_lear_users, tos_version=settings.TOS_VERSION)

            if not options["test_suite"]:
                # To keep the messages.json fixtures file for the test
                # suite fast, don't add these users and subscriptions
                # when running populate_db for the test suite

                zulip_stream_dict = {
                    "devel": {"description": "For developing"},
                    "all": {"description": "For **everything**"},
                    "announce": {"description": "For announcements",
                                 'stream_post_policy': Stream.STREAM_POST_POLICY_ADMINS},
                    "design": {"description": "For design"},
                    "support": {"description": "For support"},
                    "social": {"description": "For socializing"},
                    "test": {"description": "For testing `code`"},
                    "errors": {"description": "For errors"},
                    "sales": {"description": "For sales discussion"}
                }  # type: Dict[str, Dict[str, Any]]

                # Calculate the maximum number of digits in any extra stream's
                # number, since a stream with name "Extra Stream 3" could show
                # up after "Extra Stream 29". (Used later to pad numbers with
                # 0s).
                maximum_digits = len(str(options['extra_streams'] - 1))

                for i in range(options['extra_streams']):
                    # Pad the number with 0s based on `maximum_digits`.
                    number_str = str(i).zfill(maximum_digits)

                    extra_stream_name = 'Extra Stream ' + number_str

                    zulip_stream_dict[extra_stream_name] = {
                        "description": "Auto-generated extra stream.",
                    }

                bulk_create_streams(zulip_realm, zulip_stream_dict)
                # Now that we've created the notifications stream, configure it properly.
                zulip_realm.notifications_stream = get_stream("announce", zulip_realm)
                zulip_realm.save(update_fields=['notifications_stream'])

                # Add a few default streams
                for default_stream_name in ["design", "devel", "social", "support"]:
                    DefaultStream.objects.create(realm=zulip_realm,
                                                 stream=get_stream(default_stream_name, zulip_realm))

                # Now subscribe everyone to these streams
                subscribe_users_to_streams(zulip_realm, zulip_stream_dict)

                # These bots are not needed by the test suite
                internal_zulip_users_nosubs = [
                    ("Zulip Commit Bot", "commit-bot@zulip.com"),
                    ("Zulip Trac Bot", "trac-bot@zulip.com"),
                    ("Zulip Nagios Bot", "nagios-bot@zulip.com"),
                ]
                create_users(zulip_realm, internal_zulip_users_nosubs, bot_type=UserProfile.DEFAULT_BOT)

            # Mark all messages as read
            UserMessage.objects.all().update(flags=UserMessage.flags.read)

            if not options["test_suite"]:
                # Update pointer of each user to point to the last message in their
                # UserMessage rows with sender_id=user_profile_id.
                users = list(UserMessage.objects.filter(
                    message__sender_id=F('user_profile_id')).values(
                    'user_profile_id').annotate(pointer=Max('message_id')))
                for user in users:
                    UserProfile.objects.filter(id=user['user_profile_id']).update(
                        pointer=user['pointer'])

            create_user_groups()

            if not options["test_suite"]:
                # We populate the analytics database here for
                # development purpose only
                call_command('populate_analytics_db')
            self.stdout.write("Successfully populated test database.\n")

recipient_hash = {}  # type: Dict[int, Recipient]
def get_recipient_by_id(rid: int) -> Recipient:
    if rid in recipient_hash:
        return recipient_hash[rid]
    return Recipient.objects.get(id=rid)

# Create some test messages, including:
# - multiple streams
# - multiple subjects per stream
# - multiple huddles
# - multiple personals converastions
# - multiple messages per subject
# - both single and multi-line content
def generate_and_send_messages(data: Tuple[int, Sequence[Sequence[int]], Mapping[str, Any],
                                           Callable[[str], Any], int]) -> int:
    (tot_messages, personals_pairs, options, output, random_seed) = data
    random.seed(random_seed)

    with open(os.path.join(get_or_create_dev_uuid_var_path('test-backend'),
                           "test_messages.json"), "r") as infile:
        dialog = ujson.load(infile)
    random.shuffle(dialog)
    texts = itertools.cycle(dialog)

    recipient_streams = [klass.id for klass in
                         Recipient.objects.filter(type=Recipient.STREAM)]  # type: List[int]
    recipient_huddles = [h.id for h in Recipient.objects.filter(type=Recipient.HUDDLE)]  # type: List[int]

    huddle_members = {}  # type: Dict[int, List[int]]
    for h in recipient_huddles:
        huddle_members[h] = [s.user_profile.id for s in
                             Subscription.objects.filter(recipient_id=h)]

    message_batch_size = options['batch_size']
    num_messages = 0
    random_max = 1000000
    recipients = {}  # type: Dict[int, Tuple[int, int, Dict[str, Any]]]
    messages = []
    while num_messages < tot_messages:
        saved_data = {}  # type: Dict[str, Any]
        message = Message()
        message.sending_client = get_client('populate_db')

        message.content = next(texts)

        randkey = random.randint(1, random_max)
        if (num_messages > 0 and
                random.randint(1, random_max) * 100. / random_max < options["stickyness"]):
            # Use an old recipient
            message_type, recipient_id, saved_data = recipients[num_messages - 1]
            if message_type == Recipient.PERSONAL:
                personals_pair = saved_data['personals_pair']
                random.shuffle(personals_pair)
            elif message_type == Recipient.STREAM:
                message.subject = saved_data['subject']
                message.recipient = get_recipient_by_id(recipient_id)
            elif message_type == Recipient.HUDDLE:
                message.recipient = get_recipient_by_id(recipient_id)
        elif (randkey <= random_max * options["percent_huddles"] / 100.):
            message_type = Recipient.HUDDLE
            message.recipient = get_recipient_by_id(random.choice(recipient_huddles))
        elif (randkey <= random_max * (options["percent_huddles"] + options["percent_personals"]) / 100.):
            message_type = Recipient.PERSONAL
            personals_pair = random.choice(personals_pairs)
            random.shuffle(personals_pair)
        elif (randkey <= random_max * 1.0):
            message_type = Recipient.STREAM
            message.recipient = get_recipient_by_id(random.choice(recipient_streams))

        if message_type == Recipient.HUDDLE:
            sender_id = random.choice(huddle_members[message.recipient.id])
            message.sender = get_user_profile_by_id(sender_id)
        elif message_type == Recipient.PERSONAL:
            message.recipient = Recipient.objects.get(type=Recipient.PERSONAL,
                                                      type_id=personals_pair[0])
            message.sender = get_user_profile_by_id(personals_pair[1])
            saved_data['personals_pair'] = personals_pair
        elif message_type == Recipient.STREAM:
            stream = Stream.objects.get(id=message.recipient.type_id)
            # Pick a random subscriber to the stream
            message.sender = random.choice(Subscription.objects.filter(
                recipient=message.recipient)).user_profile
            message.subject = stream.name + str(random.randint(1, 3))
            saved_data['subject'] = message.subject

        message.date_sent = choose_date_sent(num_messages, tot_messages, options['threads'])
        messages.append(message)

        recipients[num_messages] = (message_type, message.recipient.id, saved_data)
        num_messages += 1

        if (num_messages % message_batch_size) == 0:
            # Send the batch and empty the list:
            send_messages(messages)
            messages = []

    if len(messages) > 0:
        # If there are unsent messages after exiting the loop, send them:
        send_messages(messages)

    return tot_messages

def send_messages(messages: List[Message]) -> None:
    # We disable USING_RABBITMQ here, so that deferred work is
    # executed in do_send_message_messages, rather than being
    # queued.  This is important, because otherwise, if run-dev.py
    # wasn't running when populate_db was run, a developer can end
    # up with queued events that reference objects from a previous
    # life of the database, which naturally throws exceptions.
    settings.USING_RABBITMQ = False
    do_send_messages([{'message': message} for message in messages])
    settings.USING_RABBITMQ = True

def choose_date_sent(num_messages: int, tot_messages: int, threads: int) -> datetime:
    # Spoofing time not supported with threading
    if threads != 1:
        return timezone_now()

    # Distrubutes 80% of messages starting from 5 days ago, over a period
    # of 3 days. Then, distributes remaining messages over past 24 hours.
    amount_in_first_chunk = int(tot_messages * 0.8)
    amount_in_second_chunk = tot_messages - amount_in_first_chunk
    if (num_messages < amount_in_first_chunk):
        # Distribute starting from 5 days ago, over a period
        # of 3 days:
        spoofed_date = timezone_now() - timezone_timedelta(days = 5)
        interval_size = 3 * 24 * 60 * 60 / amount_in_first_chunk
        lower_bound = interval_size * num_messages
        upper_bound = interval_size * (num_messages + 1)

    else:
        # We're in the last 20% of messages, distribute them over the last 24 hours:
        spoofed_date = timezone_now() - timezone_timedelta(days = 1)
        interval_size = 24 * 60 * 60 / amount_in_second_chunk
        lower_bound = interval_size * (num_messages - amount_in_first_chunk)
        upper_bound = interval_size * (num_messages - amount_in_first_chunk + 1)

    offset_seconds = random.uniform(lower_bound, upper_bound)
    spoofed_date += timezone_timedelta(seconds=offset_seconds)

    return spoofed_date

def create_user_groups() -> None:
    zulip = get_realm('zulip')
    members = [get_user('cordelia@zulip.com', zulip),
               get_user('hamlet@zulip.com', zulip)]
    create_user_group("hamletcharacters", members, zulip,
                      description="Characters of Hamlet")
