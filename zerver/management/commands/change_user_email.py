from __future__ import absolute_import
from __future__ import print_function

import sys

from argparse import ArgumentParser
from typing import Any

from zerver.lib.actions import do_change_user_email
from zerver.lib.management import ZulipBaseCommand

class Command(ZulipBaseCommand):
    help = """Change the email address for a user."""

    def add_arguments(self, parser):
        # type: (ArgumentParser) -> None
        self.add_realm_args(parser)
        parser.add_argument('old_email', metavar='<old email>', type=str,
                            help='email address to change')
        parser.add_argument('new_email', metavar='<new email>', type=str,
                            help='new email address')

    def handle(self, *args, **options):
        # type: (*Any, **str) -> None
        old_email = options['old_email']
        new_email = options['new_email']

        realm = self.get_realm(options)
        user_profile = self.get_user(old_email, realm)

        do_change_user_email(user_profile, new_email)
