# Generated by Django 1.11.5 on 2017-10-19 21:42

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("zerver", "0113_default_stream_group"),
    ]

    operations = [
        migrations.AddField(
            model_name="preregistrationuser",
            name="invited_as_admin",
            field=models.BooleanField(default=False),
        ),
    ]
