# -*- coding: utf-8 -*-
# Generated by Django 1.11.26 on 2020-01-08 16:44
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('zerver', '0260_missed_message_addresses_from_redis_to_db'),
    ]

    operations = [
        migrations.AddField(
            model_name='mutedtopic',
            name='scheduled_timestamp',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
