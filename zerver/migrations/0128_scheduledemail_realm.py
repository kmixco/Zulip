# Generated by Django 1.11.6 on 2017-12-05 01:08

import django.db.models.deletion
from django.db import migrations, models
from django.db.backends.postgresql.schema import DatabaseSchemaEditor
from django.db.migrations.state import StateApps


def set_realm_for_existing_scheduledemails(
    apps: StateApps, schema_editor: DatabaseSchemaEditor
) -> None:
    scheduledemail_model = apps.get_model("zerver", "ScheduledEmail")
    preregistrationuser_model = apps.get_model("zerver", "PreregistrationUser")
    for scheduledemail in scheduledemail_model.objects.all():
        if scheduledemail.type == 3:  # ScheduledEmail.INVITATION_REMINDER
            # Don't think this can be None, but just be safe
            prereg = preregistrationuser_model.objects.filter(email=scheduledemail.address).first()
            if prereg is not None:
                scheduledemail.realm = prereg.realm
        else:
            scheduledemail.realm = scheduledemail.user.realm
        scheduledemail.save(update_fields=['realm'])

    # Shouldn't be needed, but just in case
    scheduledemail_model.objects.filter(realm=None).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('zerver', '0127_disallow_chars_in_stream_and_user_name'),
    ]

    operations = [
        # Start with ScheduledEmail.realm being non-null
        migrations.AddField(
            model_name='scheduledemail',
            name='realm',
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.CASCADE, to='zerver.Realm'
            ),
        ),
        # Sets realm for existing ScheduledEmails
        migrations.RunPython(
            set_realm_for_existing_scheduledemails,
            reverse_code=migrations.RunPython.noop,
            elidable=True,
        ),
        # Require ScheduledEmail.realm to be non-null
        migrations.AlterField(
            model_name='scheduledemail',
            name='realm',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='zerver.Realm'),
        ),
    ]
