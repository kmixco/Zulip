# Generated by Django 4.2.5 on 2023-09-12 19:58

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        (
            "zerver",
            "0483_rename_escape_navigates_to_default_view_realmuserdefault_web_escape_navigates_to_home_view_and_more",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="preregistrationrealm",
            name="default_language",
            field=models.CharField(default="en", max_length=50),
        ),
    ]
