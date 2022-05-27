# Generated by Django 1.10.5 on 2017-05-02 21:44
import django.core.validators
from django.db import migrations, models
from django.db.backends.postgresql.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps


class Migration(migrations.Migration):

    dependencies = [
        ("zerver", "0080_realm_description_length"),
    ]

    def emoji_to_lowercase(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
        RealmEmoji = apps.get_model("zerver", "RealmEmoji")
        emoji = RealmEmoji.objects.all()
        for e in emoji:
            # Technically, this could create a conflict, but it's
            # exceedingly unlikely.  If that happens, the sysadmin can
            # manually rename the conflicts with the manage.py shell
            # and then rerun the migration/upgrade.
            e.name = e.name.lower()
            e.save()

    operations = [
        migrations.RunPython(emoji_to_lowercase, elidable=True),
        migrations.AlterField(
            model_name="realmemoji",
            name="name",
            field=models.TextField(
                validators=[
                    django.core.validators.MinLengthValidator(1),
                    django.core.validators.RegexValidator(
                        message="Invalid characters in emoji name",
                        regex="^[0-9a-z.\\-_]+(?<![.\\-_])$",
                    ),
                ]
            ),
        ),
    ]
