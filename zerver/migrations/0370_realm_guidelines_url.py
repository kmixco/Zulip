# Generated by Django 3.2.9 on 2021-12-03 07:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("zerver", "0369_add_escnav_default_display_user_setting"),
    ]

    operations = [
        migrations.AddField(
            model_name="realm",
            name="guidelines_url",
            field=models.URLField(null=True),
        ),
    ]
