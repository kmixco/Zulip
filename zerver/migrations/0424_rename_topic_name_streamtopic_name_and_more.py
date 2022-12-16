# Generated by Django 4.1.3 on 2022-12-12 08:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("zerver", "0423_add_streamtopic_model"),
    ]

    operations = [
        migrations.RenameField(
            model_name="streamtopic",
            old_name="topic_name",
            new_name="name",
        ),
        migrations.AlterUniqueTogether(
            name="streamtopic",
            unique_together={("stream", "name")},
        ),
        migrations.AlterField(
            model_name="streamtopic",
            name="id",
            field=models.AutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
    ]
