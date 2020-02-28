# -*- coding: utf-8 -*-
# Generated by Django 1.11.24 on 2019-10-03 22:27
from __future__ import unicode_literals

from django.db import migrations, models
from django.db.backends.postgresql_psycopg2.schema import DatabaseSchemaEditor
from django.db.migrations.state import StateApps

# The values at the time of this migration
ROLE_REALM_ADMINISTRATOR = 200
ROLE_MEMBER = 400
ROLE_GUEST = 600

def update_role(apps: StateApps, schema_editor: DatabaseSchemaEditor) -> None:
    UserProfile = apps.get_model('zerver', 'UserProfile')
    for user in UserProfile.objects.all():
        if user.is_realm_admin:
            user.role = ROLE_REALM_ADMINISTRATOR
        elif user.is_guest:
            user.role = ROLE_GUEST
        else:
            user.role = ROLE_MEMBER
        user.save(update_fields=['role'])

def reverse_code(apps: StateApps, schema_editor: DatabaseSchemaEditor) -> None:
    UserProfile = apps.get_model('zerver', 'UserProfile')
    for user in UserProfile.objects.all():
        if user.role == ROLE_REALM_ADMINISTRATOR:
            user.is_realm_admin = True
            user.save(update_fields=['is_realm_admin'])
        elif user.role == ROLE_GUEST:
            user.is_guest = True
            user.save(update_fields=['is_guest'])

class Migration(migrations.Migration):

    dependencies = [
        ('zerver', '0247_realmauditlog_event_type_to_int'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='role',
            field=models.PositiveSmallIntegerField(null=True),
        ),

        migrations.RunPython(update_role, reverse_code=reverse_code),
    ]
