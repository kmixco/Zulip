# Generated by Django 1.10.5 on 2017-01-25 20:55
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("zerver", "0050_userprofile_avatar_version"),
    ]

    operations = [
        migrations.AddField(
            model_name="realmalias",
            name="allow_subdomains",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterUniqueTogether(
            name="realmalias",
            unique_together={("realm", "domain")},
        ),
    ]
