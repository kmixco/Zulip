# -*- coding: utf-8 -*-
# Generated by Django 1.11.26 on 2020-01-17 15:26
from __future__ import unicode_literals

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('zerver', '0261_realm_private_message_policy'),
    ]

    operations = [
        migrations.AddField(
            model_name='mutedtopic',
            name='date_muted',
            field=models.DateTimeField(default=datetime.datetime(2020, 1, 1, 0, 0)),
        ),
    ]
