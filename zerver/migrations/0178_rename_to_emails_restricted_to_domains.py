# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2018-07-27 21:47
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('zerver', '0177_user_message_add_and_index_is_private_flag'),
    ]

    operations = [
        migrations.RenameField(
            model_name='realm',
            old_name='restricted_to_domain',
            new_name='emails_restricted_to_domains',
        ),
    ]
