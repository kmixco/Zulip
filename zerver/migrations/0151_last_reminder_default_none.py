# Generated by Django 1.11.6 on 2018-03-29 18:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("zerver", "0150_realm_allow_community_topic_editing"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userprofile",
            name="last_reminder",
            field=models.DateTimeField(default=None, null=True),
        ),
    ]
