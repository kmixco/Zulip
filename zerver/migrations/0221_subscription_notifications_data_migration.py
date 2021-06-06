# Generated by Django 1.11.18 on 2019-02-13 20:13

from django.db import migrations
from django.db.backends.postgresql.schema import DatabaseSchemaEditor
from django.db.migrations.state import StateApps

RECIPIENT_STREAM = 2
SETTINGS_MAP = {
    "desktop_notifications": "enable_stream_desktop_notifications",
    "audible_notifications": "enable_stream_sounds",
    "push_notifications": "enable_stream_push_notifications",
    "email_notifications": "enable_stream_email_notifications",
}


def update_notification_settings(apps: StateApps, schema_editor: DatabaseSchemaEditor) -> None:
    Subscription = apps.get_model("zerver", "Subscription")
    UserProfile = apps.get_model("zerver", "UserProfile")

    for setting_value in [True, False]:
        for sub_setting_name, user_setting_name in SETTINGS_MAP.items():
            sub_filter_kwargs = {sub_setting_name: setting_value}
            user_filter_kwargs = {user_setting_name: setting_value}
            update_kwargs = {sub_setting_name: None}
            Subscription.objects.filter(
                user_profile__in=UserProfile.objects.filter(**user_filter_kwargs),
                recipient__type=RECIPIENT_STREAM,
                **sub_filter_kwargs,
            ).update(**update_kwargs)


def reverse_notification_settings(apps: StateApps, schema_editor: DatabaseSchemaEditor) -> None:
    Subscription = apps.get_model("zerver", "Subscription")
    UserProfile = apps.get_model("zerver", "UserProfile")

    for setting_value in [True, False]:
        for sub_setting_name, user_setting_name in SETTINGS_MAP.items():
            sub_filter_kwargs = {sub_setting_name: None}
            user_filter_kwargs = {user_setting_name: setting_value}
            update_kwargs = {sub_setting_name: setting_value}
            Subscription.objects.filter(
                user_profile__in=UserProfile.objects.filter(**user_filter_kwargs),
                recipient__type=RECIPIENT_STREAM,
                **sub_filter_kwargs,
            ).update(**update_kwargs)

    for sub_setting_name, user_setting_name in SETTINGS_MAP.items():
        sub_filter_kwargs = {sub_setting_name: None}
        update_kwargs = {sub_setting_name: True}
        Subscription.objects.filter(recipient__type__in=[1, 3], **sub_filter_kwargs).update(
            **update_kwargs
        )


class Migration(migrations.Migration):

    dependencies = [
        ("zerver", "0220_subscription_notification_settings"),
    ]

    operations = [
        migrations.RunPython(
            update_notification_settings, reverse_notification_settings, elidable=True
        ),
    ]
