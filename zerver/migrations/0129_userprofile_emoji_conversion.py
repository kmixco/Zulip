# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2017-12-29 17:27
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('zerver', '0128_scheduledemail_realm'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='emoji_conversion',
            field=models.BooleanField(default=False),
        ),
    ]
