# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2017-01-16 20:50
from django.conf import settings
from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0006_add_subgroup_to_unique_constraints'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='installationcount',
            unique_together=set([('property', 'subgroup', 'end_time')]),
        ),
        migrations.RemoveField(
            model_name='installationcount',
            name='interval',
        ),
        migrations.AlterUniqueTogether(
            name='realmcount',
            unique_together=set([('realm', 'property', 'subgroup', 'end_time')]),
        ),
        migrations.RemoveField(
            model_name='realmcount',
            name='interval',
        ),
        migrations.AlterUniqueTogether(
            name='streamcount',
            unique_together=set([('stream', 'property', 'subgroup', 'end_time')]),
        ),
        migrations.RemoveField(
            model_name='streamcount',
            name='interval',
        ),
        migrations.AlterUniqueTogether(
            name='usercount',
            unique_together=set([('user', 'property', 'subgroup', 'end_time')]),
        ),
        migrations.RemoveField(
            model_name='usercount',
            name='interval',
        ),
    ]
