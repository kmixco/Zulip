# Generated by Django 4.2.9 on 2024-02-07 16:42

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("zerver", "0498_rename_notifications_stream_realm_new_stream_announcements_stream"),
    ]

    operations = [
        migrations.RenameField(
            model_name="realm",
            old_name="signup_notifications_stream",
            new_name="signup_announcements_stream",
        ),
    ]
