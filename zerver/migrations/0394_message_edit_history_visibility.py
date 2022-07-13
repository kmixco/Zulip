# Generated by Django 3.2.13 on 2022-05-17 06:34

from django.db import migrations, models
from django.db.backends.postgresql.schema import DatabaseSchemaEditor
from django.db.migrations.state import StateApps


def change_bool_to_int(apps: StateApps, schema_editor: DatabaseSchemaEditor) -> None:
    Realm = apps.get_model("zerver", "Realm")
    for realm in Realm.objects.all():
        if realm.allow_edit_history:
            realm.message_edit_history_visibility = 1
        else:
            realm.message_edit_history_visibility = 3
        realm.save()


class Migration(migrations.Migration):

    dependencies = [
        ("zerver", "0393_realm_want_advertise_in_communities_directory"),
    ]

    operations = [
        migrations.AddField(
            model_name="realm",
            name="message_edit_history_visibility",
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.RunPython(change_bool_to_int),
        migrations.RemoveField(
            model_name="realm",
            name="allow_edit_history",
        ),
    ]
