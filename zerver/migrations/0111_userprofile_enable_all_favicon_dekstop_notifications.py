# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2017-10-16 08:20
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('zerver', '0110_stream_is_in_zephyr_realm'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='enable_all_favicon_dekstop_notifications',
            field=models.BooleanField(default=True),
        ),
    ]
