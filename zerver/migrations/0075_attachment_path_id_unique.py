# Generated by Django 1.10.5 on 2017-04-13 22:29
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('zerver', '0074_fix_duplicate_attachments'),
    ]

    operations = [
        migrations.AlterField(
            model_name='archivedattachment',
            name='path_id',
            field=models.TextField(db_index=True, unique=True),
        ),
        migrations.AlterField(
            model_name='attachment',
            name='path_id',
            field=models.TextField(db_index=True, unique=True),
        ),
    ]
