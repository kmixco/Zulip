# Generated by Django 2.2.17 on 2020-12-20 14:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("zerver", "0308_remove_reduntant_realm_meta_permissions"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="can_create_users",
            field=models.BooleanField(db_index=True, default=False),
        ),
    ]
