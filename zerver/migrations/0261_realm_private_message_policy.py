# -*- coding: utf-8 -*-
# Generated by Django 1.11.26 on 2020-01-08 00:32
from __future__ import unicode_literals

from django.db import migrations, models


PRIVATE_MESSAGE_POLICY_UNLIMITED = 1
class Migration(migrations.Migration):

    dependencies = [
        ('zerver', '0260_missed_message_addresses_from_redis_to_db'),
    ]

    operations = [
        migrations.AddField(
            model_name='realm',
            name='private_message_policy',
            field=models.PositiveSmallIntegerField(default=PRIVATE_MESSAGE_POLICY_UNLIMITED),
        ),
    ]
