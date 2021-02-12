# Generated by Django 1.11.24 on 2019-10-03 00:10

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('zilencer', '0017_installationcount_indexes'),
    ]

    operations = [
        migrations.CreateModel(
            name='RemoteRealmAuditLog',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('realm_id', models.IntegerField(db_index=True)),
                ('remote_id', models.IntegerField(db_index=True)),
                ('event_time', models.DateTimeField(db_index=True)),
                ('backfilled', models.BooleanField(default=False)),
                ('extra_data', models.TextField(null=True)),
                ('event_type', models.PositiveSmallIntegerField()),
                (
                    'server',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to='zilencer.RemoteZulipServer'
                    ),
                ),
            ],
        ),
    ]
