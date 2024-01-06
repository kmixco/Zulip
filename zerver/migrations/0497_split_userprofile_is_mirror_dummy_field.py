# Generated by Django 4.2.6 on 2023-10-24 09:23

from django.db import migrations, models
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps


def split_dummy_field(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """
    Splits is_mirror_dummy into three fields
        - is_mirror_protouser, set True if realm.is_zephyr_mirror_realm = True
        - is_imported_protouser, set True if realm.is_zephyr_mirror_realm = False
        - is_deleted_protouser, set True delete entry is found in RealmAuditLog

    Another requirement for each field in order to be set to True is that also
    is_mirror_dummy is True.
    """

    UserProfile = apps.get_model("zerver", "UserProfile")
    RealmAuditLog = apps.get_model("zerver", "RealmAuditLog")

    for user_profile in UserProfile.objects.all():
        if user_profile.is_mirror_dummy:
            deleted_record = RealmAuditLog.objects.filter(
                modified_user=user_profile, event_type=RealmAuditLog.USER_DELETED
            )
            if deleted_record.exists():
                user_profile.is_deleted_protouser = True
            elif user_profile.realm.is_zephyr_mirror_realm:
                user_profile.is_mirror_protouser = True
            else:
                user_profile.is_imported_protouser = True


def reverse_code(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    UserProfile = apps.get_model("zerver", "UserProfile")
    for user_profile in UserProfile.objects.all():
        user_profile.is_mirror_dummy = (
            user_profile.is_mirror_protouser
            or user_profile.is_imported_protouser
            or user_profile.is_deleted_protouser
        )


class Migration(migrations.Migration):
    dependencies = [
        ("zerver", "0496_alter_scheduledmessage_read_by_sender"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="is_imported_protouser",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="is_deleted_protouser",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="is_mirror_protouser",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(
            split_dummy_field,
            reverse_code=reverse_code,
        ),
        migrations.RemoveField(model_name="userprofile", name="is_mirror_dummy"),
    ]
