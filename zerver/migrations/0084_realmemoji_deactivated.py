# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-05-22 14:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('zerver', '0083_index_mentioned_user_messages'),
    ]

    operations = [
        migrations.AddField(
            model_name='realmemoji',
            name='deactivated',
            field=models.BooleanField(default=False),
        ),
    ]
