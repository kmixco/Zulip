# Generated by Django 1.11.20 on 2019-05-09 06:54

from typing import Any, Dict, Optional

from django.db import migrations, models
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps

# We include a copy of this structure as it was at the time this
# migration was merged, since future should not impact the migration.
VIDEO_CHAT_PROVIDERS = {
    "jitsi_meet": {
        "name": "Jitsi",
        "id": 1,
    },
    "google_hangouts": {
        "name": "Google Hangouts",
        "id": 2,
    },
    "zoom": {
        "name": "Zoom",
        "id": 3,
    },
}


def get_video_chat_provider_detail(
    providers_dict: Dict[str, Dict[str, Any]],
    p_name: Optional[str] = None,
    p_id: Optional[int] = None,
) -> Dict[str, Any]:
    for provider in providers_dict.values():
        if p_name and provider["name"] == p_name:
            return provider
        if p_id and provider["id"] == p_id:
            return provider
    return {}


def update_existing_video_chat_provider_values(
    apps: StateApps, schema_editor: BaseDatabaseSchemaEditor
) -> None:
    Realm = apps.get_model("zerver", "Realm")

    for realm in Realm.objects.all():
        realm.video_chat_provider = get_video_chat_provider_detail(
            VIDEO_CHAT_PROVIDERS, p_name=realm.video_chat_provider_old
        )["id"]
        realm.save(update_fields=["video_chat_provider"])


def reverse_code(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    Realm = apps.get_model("zerver", "Realm")

    for realm in Realm.objects.all():
        realm.video_chat_provider_old = get_video_chat_provider_detail(
            VIDEO_CHAT_PROVIDERS, p_id=realm.video_chat_provider
        )["name"]
        realm.save(update_fields=["video_chat_provider_old"])


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("zerver", "0223_rename_to_is_muted"),
    ]

    operations = [
        migrations.RenameField(
            model_name="realm",
            old_name="video_chat_provider",
            new_name="video_chat_provider_old",
        ),
        migrations.AddField(
            model_name="realm",
            name="video_chat_provider",
            field=models.PositiveSmallIntegerField(
                default=VIDEO_CHAT_PROVIDERS["jitsi_meet"]["id"]
            ),
        ),
        migrations.RunPython(
            update_existing_video_chat_provider_values, reverse_code=reverse_code, elidable=True
        ),
        migrations.RemoveField(
            model_name="realm",
            name="video_chat_provider_old",
        ),
    ]
