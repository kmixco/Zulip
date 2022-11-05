# Generated by Django 4.1.2 on 2022-10-21 06:31

from django.db import migrations
from django.db.backends.postgresql.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps


def migrate_pronouns_custom_profile_fields(
    apps: StateApps, schema_editor: BaseDatabaseSchemaEditor
) -> None:
    CustomProfileField = apps.get_model("zerver", "CustomProfileField")
    SHORT_TEXT = 1
    PRONOUNS = 8

    CustomProfileField.objects.filter(field_type=SHORT_TEXT, name__icontains="pronoun").update(
        field_type=PRONOUNS
    )


def reverse_migrate_pronouns_custom_profile_fields(
    apps: StateApps, schema_editor: BaseDatabaseSchemaEditor
) -> None:
    CustomProfileField = apps.get_model("zerver", "CustomProfileField")
    SHORT_TEXT = 1
    PRONOUNS = 8

    CustomProfileField.objects.filter(field_type=PRONOUNS).update(field_type=SHORT_TEXT)


class Migration(migrations.Migration):

    dependencies = [
        ("zerver", "0420_alter_archivedmessage_realm_alter_message_realm"),
    ]

    operations = [
        migrations.RunPython(
            migrate_pronouns_custom_profile_fields,
            reverse_code=reverse_migrate_pronouns_custom_profile_fields,
            elidable=True,
        ),
    ]
