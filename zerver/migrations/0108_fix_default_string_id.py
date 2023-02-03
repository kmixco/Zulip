# Generated by Django 1.11.4 on 2017-08-24 02:39
from django.db import migrations
from django.db.backends.postgresql.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps


def fix_realm_string_ids(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    Realm = apps.get_model("zerver", "Realm")
    if Realm.objects.filter(deactivated=False).count() != 2:
        return

    zulip_realm = Realm.objects.get(string_id="zulip")
    try:
        user_realm = Realm.objects.filter(deactivated=False).exclude(id=zulip_realm.id)[0]
    except Realm.DoesNotExist:
        return

    user_realm.string_id = ""
    user_realm.save()


class Migration(migrations.Migration):
    dependencies = [
        ("zerver", "0107_multiuseinvite"),
    ]

    operations = [
        migrations.RunPython(
            fix_realm_string_ids, reverse_code=migrations.RunPython.noop, elidable=True
        ),
    ]
