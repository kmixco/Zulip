# Generated by Django 3.2.2 on 2021-06-01 16:19

from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps


def create_realm_user_default_table(
    apps: StateApps, schema_editor: BaseDatabaseSchemaEditor
) -> None:
    Realm = apps.get_model("zerver", "Realm")
    RealmUserDefault = apps.get_model("zerver", "RealmUserDefault")
    realms = Realm.objects.all()
    realm_user_default_objects = []
    for realm in realms:
        realm_user_default = RealmUserDefault(realm=realm)
        realm_user_default_objects.append(realm_user_default)
    RealmUserDefault.objects.bulk_create(realm_user_default_objects)


class Migration(migrations.Migration):
    dependencies = [
        ("zerver", "0345_alter_realm_name"),
    ]

    operations = [
        migrations.RunPython(
            create_realm_user_default_table, reverse_code=migrations.RunPython.noop, elidable=True
        ),
    ]
