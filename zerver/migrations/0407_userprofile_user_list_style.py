# Generated by Django 4.0.6 on 2022-08-14 18:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("zerver", "0406_alter_realm_message_content_edit_limit_seconds"),
    ]

    operations = [
        migrations.AddField(
            model_name="realmuserdefault",
            name="user_list_style",
            field=models.PositiveSmallIntegerField(default=2),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="user_list_style",
            field=models.PositiveSmallIntegerField(default=2),
        ),
    ]
