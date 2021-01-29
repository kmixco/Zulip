# Generated by Django 3.1.5 on 2021-01-10 11:30

from django.db import migrations, models


class Migration(migrations.Migration):
    """
    This doesn't actually run any SQL, it's for Django's internal
    tracking of changes to models only.
    django.contrib.postgres.fields.JSONField is deprecated as of Django 3.1
    and should be replaced by models.JSONField which offers the same functionality.
    """

    dependencies = [
        ('zerver', '0309_userprofile_can_create_users'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='zoom_token',
            field=models.JSONField(default=None, null=True),
        ),
    ]
