# Generated by Django 3.1.8 on 2021-05-03 04:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("zerver", "0323_show_starred_message_counts"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="timezone_auto_update",
            field=models.BooleanField(default=True),
        ),
    ]
