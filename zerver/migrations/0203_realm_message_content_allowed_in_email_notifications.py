# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2019-01-07 11:46
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('zerver', '0202_add_user_status_info'),
    ]

    operations = [
        migrations.AddField(
            model_name='realm',
            name='message_content_allowed_in_email_notifications',
            field=models.BooleanField(default=True),
        ),
    ]
