# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2018-01-24 20:24
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('zerver', '0135_scheduledmessage_delivery_type'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userprofile',
            name='quota',
        ),
    ]
