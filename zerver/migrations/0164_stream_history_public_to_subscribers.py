# Generated by Django 1.11.11 on 2018-04-28 22:31

from django.conf import settings
from django.db import migrations, models
from django.db.backends.postgresql.schema import DatabaseSchemaEditor
from django.db.migrations.state import StateApps


def set_initial_value_for_history_public_to_subscribers(
    apps: StateApps, schema_editor: DatabaseSchemaEditor
) -> None:
    stream_model = apps.get_model("zerver", "Stream")
    streams = stream_model.objects.all()

    for stream in streams:
        if stream.invite_only:
            stream.history_public_to_subscribers = getattr(
                settings, 'PRIVATE_STREAM_HISTORY_FOR_SUBSCRIBERS', False
            )
        else:
            stream.history_public_to_subscribers = True

        if stream.is_in_zephyr_realm:
            stream.history_public_to_subscribers = False

        stream.save(update_fields=["history_public_to_subscribers"])


class Migration(migrations.Migration):

    dependencies = [
        ('zerver', '0163_remove_userprofile_default_desktop_notifications'),
    ]

    operations = [
        migrations.AddField(
            model_name='stream',
            name='history_public_to_subscribers',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(
            set_initial_value_for_history_public_to_subscribers,
            reverse_code=migrations.RunPython.noop,
            elidable=True,
        ),
    ]
