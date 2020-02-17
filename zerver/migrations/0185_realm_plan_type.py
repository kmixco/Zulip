# -*- coding: utf-8 -*-
# Generated by Django 1.11.14 on 2018-08-10 21:36
from __future__ import unicode_literals

from django.db import migrations, models


SELF_HOSTED = 1
class Migration(migrations.Migration):

    dependencies = [
        ('zerver', '0184_rename_custom_field_types'),
    ]

    operations = [
        migrations.AddField(
            model_name='realm',
            name='plan_type',
            # Realm.SELF_HOSTED
            field=models.PositiveSmallIntegerField(default=SELF_HOSTED),
        ),
    ]
