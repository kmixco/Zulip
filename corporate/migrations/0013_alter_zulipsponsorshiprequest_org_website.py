# Generated by Django 3.2.5 on 2021-08-06 19:18

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("corporate", "0012_zulipsponsorshiprequest"),
    ]

    operations = [
        migrations.AlterField(
            model_name="zulipsponsorshiprequest",
            name="org_website",
            field=models.URLField(blank=True, null=True),
        ),
    ]
