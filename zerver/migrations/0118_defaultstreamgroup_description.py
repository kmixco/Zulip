# Generated by Django 1.11.6 on 2017-11-14 19:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("zerver", "0117_add_desc_to_user_group"),
    ]

    operations = [
        migrations.AddField(
            model_name="defaultstreamgroup",
            name="description",
            field=models.CharField(default="", max_length=1024),
        ),
    ]
