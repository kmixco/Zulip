# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2018-01-13 11:54
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('zerver', '0133_rename_botuserconfigdata_botconfigdata'),
        ('zilencer', '0005_remotepushdevicetoken_fix_uniqueness'),
    ]

    operations = [
        migrations.CreateModel(
            name='Customer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stripe_customer_id', models.CharField(max_length=255, unique=True)),
                ('realm', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='zerver.Realm')),
            ],
        ),
    ]
