# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-04-23 02:47
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('zerver', '0214_realm_invite_to_stream_policy'),
    ]

    operations = [
        migrations.AddField(
            model_name='realm',
            name='avatar_changes_disabled',
            field=models.BooleanField(default=False),
        ),
    ]
