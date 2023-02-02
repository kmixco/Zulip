# Generated by Django 3.1.7 on 2021-04-01 19:27

from django.db import migrations
from django.db.backends.postgresql.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps


def migrate_to_invite_to_realm_policy(
    apps: StateApps, schema_editor: BaseDatabaseSchemaEditor
) -> None:
    Realm = apps.get_model("zerver", "Realm")
    Realm.INVITE_TO_REALM_POLICY_MEMBERS_ONLY = 1
    Realm.INVITE_TO_REALM_POLICY_ADMINS_ONLY = 2
    Realm.objects.filter(invite_by_admins_only=False).update(
        invite_to_realm_policy=Realm.INVITE_TO_REALM_POLICY_MEMBERS_ONLY
    )
    Realm.objects.filter(invite_by_admins_only=True).update(
        invite_to_realm_policy=Realm.INVITE_TO_REALM_POLICY_ADMINS_ONLY
    )


class Migration(migrations.Migration):
    dependencies = [
        ("zerver", "0316_realm_invite_to_realm_policy"),
    ]

    operations = [
        migrations.RunPython(
            migrate_to_invite_to_realm_policy, reverse_code=migrations.RunPython.noop, elidable=True
        ),
    ]
