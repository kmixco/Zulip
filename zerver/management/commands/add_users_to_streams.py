from __future__ import absolute_import
from __future__ import print_function

from typing import Any

from django.core.management.base import CommandParser

from zerver.lib.actions import create_stream_if_needed, bulk_add_subscriptions
from zerver.lib.management import ZulipBaseCommand
from zerver.models import UserProfile

class Command(ZulipBaseCommand):
    help = """Add some or all users in a realm to a set of streams."""

    def add_arguments(self, parser):
        # type: (CommandParser) -> None
        self.add_realm_args(parser)

        parser.add_argument(
            '-s', '--streams',
            dest='streams',
            type=str,
            help='A comma-separated list of stream names.')

        parser.add_argument(
            '-u', '--users',
            dest='users',
            type=str,
            help='A comma-separated list of email addresses.')

        parser.add_argument(
            '-a', '--all-users',
            dest='all_users',
            action="store_true",
            default=False,
            help='Add all users in this realm to these streams.')

    def handle(self, **options):
        # type: (**Any) -> None
        if options["streams"] is None or \
                (options["users"] is None and not options["all_users"]):
            self.print_help("./manage.py", "add_users_to_streams")
            exit(1)

        stream_names = set([stream.strip() for stream in options["streams"].split(",")])
        realm = self.get_realm(options)

        if options["all_users"]:
            user_profiles = UserProfile.objects.filter(realm=realm)
        else:
            emails = set([email.strip() for email in options["users"].split(",")])
            user_profiles = []
            for email in emails:
                user_profiles.append(self.get_user(email, realm))

        for stream_name in set(stream_names):
            for user_profile in user_profiles:
                stream, _ = create_stream_if_needed(user_profile.realm, stream_name)
                _ignore, already_subscribed = bulk_add_subscriptions([stream], [user_profile])
                was_there_already = user_profile.id in {tup[0].id for tup in already_subscribed}
                print("%s %s to %s" % (
                    "Already subscribed" if was_there_already else "Subscribed",
                    user_profile.email, stream_name))
