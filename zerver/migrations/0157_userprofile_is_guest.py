# -*- coding: utf-8 -*-
# Generated by Django 1.11.11 on 2018-04-20 19:29
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('zerver', '0156_add_hint_to_profile_field'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='is_guest',
            field=models.BooleanField(db_index=True, default=False),
        ),
    ]
