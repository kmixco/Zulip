# Generated by Django 5.0.6 on 2024-06-23 00:29

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("zilencer", "0063_convert_ids_to_bigints"),
    ]

    operations = [
        migrations.AddField(
            model_name="remotezulipserver",
            name="last_merge_base",
            field=models.CharField(max_length=128, null=True),
        ),
    ]
