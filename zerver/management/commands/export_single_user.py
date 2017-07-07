from __future__ import absolute_import
from __future__ import print_function

from typing import Any

from argparse import ArgumentParser
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError

import os
import shutil
import subprocess
import tempfile
import ujson

from zerver.lib.export import do_export_user
from zerver.models import UserProfile, get_realm, get_user_for_mgmt

class Command(BaseCommand):
    help = """Exports message data from a Zulip user

    This command exports the message history for a single Zulip user.

    Note that this only exports the user's message history and
    realm-public metadata needed to understand it; it does nothing
    with (for example) any bots owned by the user."""

    def add_arguments(self, parser):
        # type: (ArgumentParser) -> None
        parser.add_argument(
            '-r', '--realm', nargs='?', default=None,
            dest='string_id',
            type=str,
            help='The name of the realm from which you are exporting a single user.')

        parser.add_argument('email', metavar='<email>', type=str,
                            help="email of user to export")

        parser.add_argument('--output',
                            dest='output_dir',
                            action="store",
                            default=None,
                            help='Directory to write exported data to.')

    def handle(self, *args, **options):
        # type: (*Any, **Any) -> None
        email = options['email']
        realm = get_realm(options["string_id"])
        if options["string_id"] is not None and realm is None:
            print("The realm %s does not exist. Aborting." % options["string_id"])
            exit(1)
        try:
            user_profile = get_user_for_mgmt(email, realm)
        except UserProfile.DoesNotExist:
            if realm is None:
                print("e-mail %s doesn't exist in the system, skipping" % (email,))
            else:
                print("e-mail %s doesn't exist in the realm, skipping" % (email,))
            exit(1)

        output_dir = options["output_dir"]
        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix="/tmp/zulip-export-")
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        os.makedirs(output_dir)
        print("Exporting user %s" % (user_profile.email,))
        do_export_user(user_profile, output_dir)
        print("Finished exporting to %s; tarring" % (output_dir,))
        tarball_path = output_dir.rstrip('/') + '.tar.gz'
        subprocess.check_call(["tar", "--strip-components=1", "-czf", tarball_path, output_dir])
        print("Tarball written to %s" % (tarball_path,))
