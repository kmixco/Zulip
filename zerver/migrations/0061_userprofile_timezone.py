# Generated by Django 1.10.5 on 2017-03-15 11:43
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("zerver", "0060_move_avatars_to_be_uid_based"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="timezone",
            field=models.CharField(default="UTC", max_length=40),
        ),
    ]
