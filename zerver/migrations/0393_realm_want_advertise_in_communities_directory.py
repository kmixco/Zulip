# Generated by Django 3.2.12 on 2022-04-22 11:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("zerver", "0392_non_nullable_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="realm",
            name="want_advertise_in_communities_directory",
            field=models.BooleanField(default=False),
        ),
    ]
