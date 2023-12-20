# Generated by Django 4.2.7 on 2023-11-29 22:43

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("zilencer", "0039_remoterealm_org_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="remoterealm",
            name="authentication_methods",
            field=models.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="remoterealm",
            name="name",
            field=models.TextField(default=""),
        ),
    ]
