# Generated by Django 1.11.26 on 2019-12-11 00:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('zerver', '0257_fix_has_link_attribute'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='enable_online_push_notifications',
            field=models.BooleanField(default=True),
        ),
    ]
