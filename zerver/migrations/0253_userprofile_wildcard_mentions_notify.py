# Generated by Django 1.11.25 on 2019-11-06 23:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("zerver", "0252_realm_user_group_edit_policy"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="wildcard_mentions_notify",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="subscription",
            name="wildcard_mentions_notify",
            field=models.NullBooleanField(default=None),
        ),
    ]
