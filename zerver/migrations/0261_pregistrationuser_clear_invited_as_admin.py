# -*- coding: utf-8 -*-
# Generated by Django 1.11.26 on 2020-06-16 22:26
from __future__ import unicode_literals

from django.db import migrations
from django.db.backends.postgresql.schema import DatabaseSchemaEditor
from django.db.migrations.state import StateApps


def clear_preregistrationuser_invited_as_admin(
        apps: StateApps, schema_editor: DatabaseSchemaEditor) -> None:
    """This migration fixes any PreregistrationUser objects that might
    have been already corrupted to have the administrator role by the
    buggy original version of migration
    0198_preregistrationuser_invited_as.

    Since invitations that create new users as administrators are
    rare, it is cleaner to just remove the role from all
    PreregistrationUser objects than to filter for just those older
    invitation objects that could have been corrupted by the original
    migration, which would have been possible using the
    django_migrations table to check the date when the buggy migration
    was run.
    """
    INVITED_AS_MEMBER = 1
    INVITED_AS_REALM_ADMIN = 2
    PreregistrationUser = apps.get_model("zerver", "PreregistrationUser")
    PreregistrationUser.objects.filter(
        invited_as=INVITED_AS_REALM_ADMIN).update(
            invited_as=INVITED_AS_MEMBER)

class Migration(migrations.Migration):

    dependencies = [
        ('zerver', '0260_missed_message_addresses_from_redis_to_db'),
    ]

    operations = [
        migrations.RunPython(
            clear_preregistrationuser_invited_as_admin,
            reverse_code=migrations.RunPython.noop
        ),
    ]
