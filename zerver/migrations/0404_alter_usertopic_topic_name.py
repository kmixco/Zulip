# Generated by Django 4.0.6 on 2022-08-13 04:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('zerver', '0403_create_role_based_groups_for_internal_realms'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usertopic',
            name='topic_name',
            field=models.CharField(max_length=200),
        ),
    ]
