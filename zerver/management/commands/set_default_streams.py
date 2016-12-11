from __future__ import absolute_import
from __future__ import print_function

from typing import Any, Text

from django.core.management.base import BaseCommand, CommandParser

from zerver.models import get_realm
from zerver.lib.actions import set_default_streams

from optparse import make_option
import sys

class Command(BaseCommand):
    help = """Set default streams for a realm

Users created under this realm will start out with these streams. This
command is not additive: if you re-run it on a domain with a different
set of default streams, those will be the new complete set of default
streams.

For example:

./manage.py set_default_streams --domain=foo.com --streams=foo,bar,baz
./manage.py set_default_streams --domain=foo.com --streams="foo,bar,baz with space"
./manage.py set_default_streams --domain=foo.com --streams=
"""

    def add_arguments(self, parser):
        # type: (CommandParser) -> None
        parser.add_argument('-d', '--domain',
                            dest='domain',
                            type=str,
                            help='The name of the existing realm to which to '
                                 'attach default streams.')

        parser.add_argument('-s', '--streams',
                            dest='streams',
                            type=str,
                            help='A comma-separated list of stream names.')

    def handle(self, **options):
        # type: (*Any, **str) -> None
        if options["domain"] is None or options["streams"] is None:
            print("Please provide both a domain name and a default \
set of streams (which can be empty, with `--streams=`).", file=sys.stderr)
            exit(1)

        stream_dict = {
            stream.strip(): {"description": stream.strip(), "invite_only": False}
            for stream in options["streams"].split(",")
        } # type: Dict[Text, Dict[Text, Any]]
        realm = get_realm(options["domain"])
        set_default_streams(realm, stream_dict)
