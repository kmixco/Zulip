# Generated by Django 2.2.12 on 2020-04-30 00:35

from django.db import migrations


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('zerver', '0278_remove_userprofile_alert_words'),
    ]

    operations = [
        migrations.RunSQL("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS zerver_message_recipient_upper_subject ON zerver_message (recipient_id, upper(subject::text), id DESC NULLS LAST);
        """),
        migrations.RunSQL("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS zerver_message_recipient_subject ON zerver_message (recipient_id, subject, id DESC NULLS LAST);
        """),
    ]
