# Generated by Django 4.2.7 on 2023-12-10 13:18

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("zerver", "0493_rename_userhotspot_to_onboardingstep"),
    ]

    operations = [
        migrations.AddField(
            model_name="realmuserdefault",
            name="automatically_follow_topics_where_mentioned",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="automatically_follow_topics_where_mentioned",
            field=models.BooleanField(default=True),
        ),
    ]
