# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-07-17 08:01
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('zerver', '0091_realm_allow_edit_history'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='disable_wrong_narrow_warning',
            field=models.BooleanField(default=False),
        ),
    ]
