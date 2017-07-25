# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-07-22 13:44
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models
import zerver.models


class Migration(migrations.Migration):

    dependencies = [
        ('zerver', '0093_subscription_event_log_backfill'),
    ]

    operations = [
        migrations.AlterField(
            model_name='realmfilter',
            name='url_format_string',
            field=models.TextField(validators=[django.core.validators.URLValidator(), zerver.models.filter_format_validator]),
        ),
    ]
