# Generated by Django 5.0.6 on 2024-06-23 19:40

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("zerver", "0540_remove_realm_create_private_stream_policy"),
    ]

    operations = [
        migrations.AddField(
            model_name="realm",
            name="custom_welcome_bot_message",
            field=models.TextField(default=""),
        ),
        migrations.AddField(
            model_name="realm",
            name="custom_welcome_bot_message_enabled",
            field=models.BooleanField(default=False),
        ),
    ]
