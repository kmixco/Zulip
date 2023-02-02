# Generated by Django 3.2.2 on 2021-05-31 16:49

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("zerver", "0331_scheduledmessagenotificationemail"),
    ]

    operations = [
        migrations.CreateModel(
            name="RealmUserDefault",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("enter_sends", models.BooleanField(null=True, default=False)),
                ("left_side_userlist", models.BooleanField(default=False)),
                ("default_language", models.CharField(default="en", max_length=50)),
                ("default_view", models.TextField(default="recent_topics")),
                ("dense_mode", models.BooleanField(default=True)),
                ("fluid_layout_width", models.BooleanField(default=False)),
                ("high_contrast_mode", models.BooleanField(default=False)),
                ("translate_emoticons", models.BooleanField(default=False)),
                ("twenty_four_hour_time", models.BooleanField(default=False)),
                ("starred_message_counts", models.BooleanField(default=True)),
                ("color_scheme", models.PositiveSmallIntegerField(default=1)),
                ("demote_inactive_streams", models.PositiveSmallIntegerField(default=1)),
                (
                    "emojiset",
                    models.CharField(
                        choices=[
                            ("google", "Google modern"),
                            ("google-blob", "Google classic"),
                            ("twitter", "Twitter"),
                            ("text", "Plain text"),
                        ],
                        default="google-blob",
                        max_length=20,
                    ),
                ),
                ("enable_stream_desktop_notifications", models.BooleanField(default=False)),
                ("enable_stream_email_notifications", models.BooleanField(default=False)),
                ("enable_stream_push_notifications", models.BooleanField(default=False)),
                ("enable_stream_audible_notifications", models.BooleanField(default=False)),
                ("notification_sound", models.CharField(default="zulip", max_length=20)),
                ("wildcard_mentions_notify", models.BooleanField(default=True)),
                ("enable_desktop_notifications", models.BooleanField(default=True)),
                ("pm_content_in_desktop_notifications", models.BooleanField(default=True)),
                ("enable_sounds", models.BooleanField(default=True)),
                ("enable_offline_email_notifications", models.BooleanField(default=True)),
                ("message_content_in_email_notifications", models.BooleanField(default=True)),
                ("enable_offline_push_notifications", models.BooleanField(default=True)),
                ("enable_online_push_notifications", models.BooleanField(default=True)),
                ("desktop_icon_count_display", models.PositiveSmallIntegerField(default=1)),
                ("enable_digest_emails", models.BooleanField(default=True)),
                ("enable_login_emails", models.BooleanField(default=True)),
                ("enable_marketing_emails", models.BooleanField(default=True)),
                ("realm_name_in_notifications", models.BooleanField(default=False)),
                ("presence_enabled", models.BooleanField(default=True)),
                (
                    "realm",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="zerver.realm"
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
