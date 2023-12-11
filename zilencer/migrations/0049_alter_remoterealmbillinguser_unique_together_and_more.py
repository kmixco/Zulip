# Generated by Django 4.2.8 on 2023-12-10 01:01

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("zilencer", "0048_remotezulipserver_last_api_feature_level"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="remoterealmbillinguser",
            unique_together={("remote_realm", "user_uuid")},
        ),
        migrations.CreateModel(
            name="PreregistrationRemoteRealmBillingUser",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("user_uuid", models.UUIDField()),
                ("email", models.EmailField(max_length=254)),
                ("status", models.IntegerField(default=0)),
                ("next_page", models.TextField(null=True)),
                ("uri_scheme", models.TextField()),
                (
                    "remote_realm",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="zilencer.remoterealm"
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
