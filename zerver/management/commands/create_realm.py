from __future__ import absolute_import
from __future__ import print_function
from optparse import make_option

from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand
from zerver.lib.actions import Realm, do_create_realm, set_default_streams, get_realm_creation_defaults
from zerver.models import RealmAlias

if settings.ZILENCER_ENABLED:
    from zilencer.models import Deployment

import re
import sys

class Command(BaseCommand):
    help = """Create a realm for the specified domain.

Usage: python manage.py create_realm --domain=foo.com --name='Foo, Inc.'"""

    option_list = BaseCommand.option_list + (
        make_option('-d', '--domain',
                    dest='domain',
                    type='str',
                    help='The domain for the realm.'),
        make_option('-n', '--name',
                    dest='name',
                    type='str',
                    help='The user-visible name for the realm.'),
        make_option('--corporate',
                    dest='org_type',
                    action="store_const",
                    const=Realm.CORPORATE,
                    help='Is a corporate org_type'),
        make_option('--community',
                    dest='org_type',
                    action="store_const",
                    const=Realm.COMMUNITY,
                    default=None,
                    help='Is a community org_type. Is the default.'),
        make_option('--deployment',
                    dest='deployment_id',
                    type='int',
                    default=None,
                    help='Optionally, the ID of the deployment you want to associate the realm with.'),
        )

    def validate_domain(self, domain):
        # type: (str) -> None
        # Domains can't contain whitespace if they are to be used in memcached
        # keys. Seems safer to leave that as the default case regardless of
        # which backing store we use.
        if re.search("\s", domain):
            raise ValueError("Domains can't contain whitespace")

        # Domains must look like domains, ie have the structure of
        # <subdomain(s)>.<tld>. One reason for this is that bots need
        # to have valid looking emails.
        if len(domain.split(".")) < 2:
            raise ValueError("Domains must contain a '.'")

        if RealmAlias.objects.filter(domain=domain).count() > 0:
            raise ValueError("Cannot create a new realm that is already an alias for an existing realm")

    def handle(self, *args, **options):
        # type: (*Any, **Any) -> None
        domain = options["domain"]
        name = options["name"]
        realm_params = get_realm_creation_defaults(org_type=options["org_type"])

        if domain is None or name is None:
            print("\033[1;31mPlease provide both a domain and name.\033[0m\n", file=sys.stderr)
            self.print_help("python manage.py", "create_realm")
            exit(1)

        if not realm_params["invite_required"] and options["deployment_id"] is not None:
            print("\033[1;31mExternal deployments cannot be open realms.\033[0m\n", file=sys.stderr)
            self.print_help("python manage.py", "create_realm")
            exit(1)
        if options["deployment_id"] is not None and not settings.ZILENCER_ENABLED:
            print("\033[1;31mExternal deployments are not supported on voyager deployments.\033[0m\n", file=sys.stderr)
            exit(1)

        self.validate_domain(domain)

        realm, created = do_create_realm(domain, name, org_type=realm_params["org_type"])
        if created:
            print(domain, "created.")
            if options["deployment_id"] is not None:
                deployment = Deployment.objects.get(id=options["deployment_id"])
                deployment.realms.add(realm)
                deployment.save()
                print("Added to deployment", str(deployment.id))
            elif settings.PRODUCTION and settings.ZILENCER_ENABLED:
                deployment = Deployment.objects.get(base_site_url="https://zulip.com/")
                deployment.realms.add(realm)
                deployment.save()
            # In the else case, we are not using the Deployments feature.

            set_default_streams(realm, ["social", "engineering"])

            print("\033[1;36mDefault streams set to social,engineering,zulip!\033[0m")
        else:
            print(domain, "already exists.")
