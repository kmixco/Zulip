# -*- coding: utf-8 -*-
# Generated by Django 1.11.14 on 2018-08-10 16:04
from __future__ import unicode_literals

from django.db import migrations, models
from django.db.backends.postgresql_psycopg2.schema import DatabaseSchemaEditor
from django.db.migrations.state import StateApps
from django.db.models import Case, Value, When

def set_initial_value_for_is_muted(apps: StateApps, schema_editor: DatabaseSchemaEditor) -> None:
    Subscription = apps.get_model("zerver", "Subscription")
    Subscription.objects.update(is_muted=Case(
        When(in_home_view=True, then=Value(False)),
        When(in_home_view=False, then=Value(True)),
    ))

def reverse_code(apps: StateApps, schema_editor: DatabaseSchemaEditor) -> None:
    Subscription = apps.get_model("zerver", "Subscription")
    Subscription.objects.update(in_home_view=Case(
        When(is_muted=True, then=Value(False)),
        When(is_muted=False, then=Value(True)),
    ))

class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('zerver', '0222_userprofile_fluid_layout_width'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscription',
            name='is_muted',
            field=models.NullBooleanField(default=False),
        ),
        migrations.RunPython(
            set_initial_value_for_is_muted,
            reverse_code=reverse_code
        ),
        migrations.RemoveField(
            model_name='subscription',
            name='in_home_view',
        ),
    ]
