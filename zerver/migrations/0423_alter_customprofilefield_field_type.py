# Generated by Django 4.1.3 on 2022-12-14 15:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("zerver", "0422_multiuseinvite_status"),
    ]

    operations = [
        migrations.AlterField(
            model_name="customprofilefield",
            name="field_type",
            field=models.PositiveSmallIntegerField(
                choices=[
                    (1, "Short text"),
                    (2, "Long text"),
                    (4, "Date picker"),
                    (5, "Link"),
                    (7, "External account"),
                    (8, "Pronouns"),
                    (9, "Phone number"),
                    (3, "List of options"),
                    (6, "Person picker"),
                ],
                default=1,
            ),
        ),
    ]
