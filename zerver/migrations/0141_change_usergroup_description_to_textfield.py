# Generated by Django 1.11.6 on 2018-02-28 17:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("zerver", "0140_realm_send_welcome_emails"),
    ]

    operations = [
        migrations.AlterField(
            model_name="usergroup",
            name="description",
            field=models.TextField(default=""),
        ),
    ]
