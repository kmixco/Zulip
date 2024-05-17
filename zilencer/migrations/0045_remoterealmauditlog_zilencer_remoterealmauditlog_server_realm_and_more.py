# Generated by Django 4.2.7 on 2023-12-05 19:33

from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("zilencer", "0044_remoterealmbillinguser"),
    ]

    operations = [
        AddIndexConcurrently(
            model_name="remoterealmauditlog",
            index=models.Index(
                condition=models.Q(("remote_realm__isnull", True)),
                fields=["server", "realm_id"],
                name="zilencer_remoterealmauditlog_server_realm",
            ),
        ),
        AddIndexConcurrently(
            model_name="remoterealmauditlog",
            index=models.Index(
                condition=models.Q(("remote_realm__isnull", True)),
                fields=["server"],
                name="zilencer_remoterealmauditlog_server",
            ),
        ),
        AddIndexConcurrently(
            model_name="remoterealmcount",
            index=models.Index(
                condition=models.Q(("remote_realm__isnull", True)),
                fields=["server", "realm_id"],
                name="zilencer_remoterealmcount_server_realm",
            ),
        ),
        AddIndexConcurrently(
            model_name="remoterealmcount",
            index=models.Index(
                condition=models.Q(("remote_realm__isnull", True)),
                fields=["server"],
                name="zilencer_remoterealmcount_server",
            ),
        ),
    ]
