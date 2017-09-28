# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-04-17 06:49

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('zerver', '0072_realmauditlog_add_index_event_time'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomProfileField',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('field_type', models.PositiveSmallIntegerField(choices=[(1, 'Integer'), (2, 'Float'), (3, 'Short Text'), (4, 'Long Text')], default=3)),
                ('realm', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='zerver.Realm')),
            ],
        ),
        migrations.CreateModel(
            name='CustomProfileFieldValue',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.TextField()),
                ('field', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='zerver.CustomProfileField')),
                ('user_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='customprofilefieldvalue',
            unique_together=set([('user_profile', 'field')]),
        ),
        migrations.AlterUniqueTogether(
            name='customprofilefield',
            unique_together=set([('realm', 'name')]),
        ),
    ]
