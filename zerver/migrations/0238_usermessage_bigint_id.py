# Generated by Django 1.11.23 on 2019-08-22 22:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('zerver', '0237_rename_zulip_realm_to_zulipinternal'),
    ]

    operations = [
        migrations.AddField(
            model_name='archivedusermessage',
            name='bigint_id',
            field=models.BigIntegerField(null=True),
        ),
        migrations.AddField(
            model_name='usermessage',
            name='bigint_id',
            field=models.BigIntegerField(null=True),
        ),
    ]
