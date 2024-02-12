# Generated by Django 4.2.10 on 2024-02-27 10:46

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("zerver", "0500_realm_zulip_update_announcements_stream"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="usergroup",
            name="can_mention_group",
        ),
        migrations.AddField(
            model_name="usergroup",
            name="can_mention_groups",
            field=models.ManyToManyField(to="zerver.usergroup"),
        ),
    ]
