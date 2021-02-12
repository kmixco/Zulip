# Generated by Django 1.11.16 on 2018-12-27 17:09

from django.db import migrations, models
from django.db.backends.postgresql.schema import DatabaseSchemaEditor
from django.db.migrations.state import StateApps


def set_initial_value_for_invited_as(apps: StateApps, schema_editor: DatabaseSchemaEditor) -> None:
    PreregistrationUser = apps.get_model("zerver", "PreregistrationUser")
    for user in PreregistrationUser.objects.all():
        if user.invited_as_admin:
            user.invited_as = 2  # PreregistrationUser.INVITE_AS['REALM_ADMIN']
        else:
            user.invited_as = 1  # PreregistrationUser.INVITE_AS['MEMBER']
        user.save(update_fields=["invited_as"])


def reverse_code(apps: StateApps, schema_editor: DatabaseSchemaEditor) -> None:
    PreregistrationUser = apps.get_model("zerver", "PreregistrationUser")
    for user in PreregistrationUser.objects.all():
        if user.invited_as == 2:  # PreregistrationUser.INVITE_AS['REALM_ADMIN']
            user.invited_as_admin = True
        else:  # PreregistrationUser.INVITE_AS['MEMBER']
            user.invited_as_admin = False
        user.save(update_fields=["invited_as_admin"])


class Migration(migrations.Migration):

    dependencies = [
        ('zerver', '0197_azure_active_directory_auth'),
    ]

    operations = [
        migrations.AddField(
            model_name='preregistrationuser',
            name='invited_as',
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.RunPython(
            set_initial_value_for_invited_as,
            reverse_code=reverse_code,
            elidable=True,
        ),
    ]
