# Generated by Django 4.0.6 on 2022-08-13 04:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("zerver", "0404_alter_usertopic_topic_name"),
    ]

    operations = [
        migrations.AlterField(
            model_name="archivedmessage",
            name="subject",
            field=models.CharField(db_index=True, max_length=200),
        )
    ]
