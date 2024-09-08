# Generated by Django 5.0.8 on 2024-08-31 08:09

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps


def backfill_creator_id_and_date_created_from_realm_audit_log(
    apps: StateApps, schema_editor: BaseDatabaseSchemaEditor
) -> None:
    RealmAuditLog = apps.get_model("zerver", "RealmAuditLog")
    RealmAuditLog.USER_GROUP_CREATED = 701
    User_group = apps.get_model("zerver", "NamedUserGroup")

    user_group_creator_updates = []
    for audit_log_entry in RealmAuditLog.objects.select_related("modified_user_group").filter(
        event_type=RealmAuditLog.USER_GROUP_CREATED,
        acting_user_id__isnull=False,
    ):
        assert audit_log_entry.modified_user_group is not None
        user_group = audit_log_entry.modified_user_group
        user_group.creator_id = audit_log_entry.acting_user_id
        user_group_creator_updates.append(user_group)

    User_group.objects.bulk_update(user_group_creator_updates, ["creator_id"], batch_size=1000)

    user_group_date_created_updates = []
    for audit_log_entry in RealmAuditLog.objects.select_related("modified_user_group").filter(
        event_type=RealmAuditLog.USER_GROUP_CREATED,
        event_time__isnull=False,
    ):
        assert audit_log_entry.modified_user_group is not None
        user_group = audit_log_entry.modified_user_group
        user_group.date_created = audit_log_entry.event_time
        user_group_date_created_updates.append(user_group)

    User_group.objects.bulk_update(
        user_group_date_created_updates, ["date_created"], batch_size=1000
    )


class Migration(migrations.Migration):
    dependencies = [
        ("zerver", "0577_merge_20240829_0153"),
    ]

    operations = [
        migrations.AddField(
            model_name="namedusergroup",
            name="creator",
            field=models.ForeignKey(
                db_column="creator",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="namedusergroup",
            name="date_created",
            field=models.DateTimeField(default=django.utils.timezone.now, null=True),
        ),
        migrations.RunPython(
            backfill_creator_id_and_date_created_from_realm_audit_log,
            reverse_code=migrations.RunPython.noop,
            elidable=True,
        ),
    ]
