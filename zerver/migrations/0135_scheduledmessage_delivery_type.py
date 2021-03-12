# Generated by Django 1.11.6 on 2018-01-12 10:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("zerver", "0134_scheduledmessage"),
    ]

    operations = [
        migrations.AddField(
            model_name="scheduledmessage",
            name="delivery_type",
            field=models.PositiveSmallIntegerField(
                choices=[(1, "send_later"), (2, "remind")], default=1
            ),
        ),
    ]
