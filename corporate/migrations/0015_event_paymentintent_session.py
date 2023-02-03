# Generated by Django 3.2.9 on 2021-11-04 16:23

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("corporate", "0014_customerplan_end_date"),
    ]

    operations = [
        migrations.CreateModel(
            name="PaymentIntent",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("stripe_payment_intent_id", models.CharField(max_length=255, unique=True)),
                ("status", models.SmallIntegerField()),
                ("last_payment_error", models.JSONField(default=None, null=True)),
                (
                    "customer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="corporate.customer"
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Session",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("stripe_session_id", models.CharField(max_length=255, unique=True)),
                ("type", models.SmallIntegerField()),
                ("status", models.SmallIntegerField(default=1)),
                (
                    "customer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="corporate.customer"
                    ),
                ),
                (
                    "payment_intent",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="corporate.paymentintent",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Event",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("stripe_event_id", models.CharField(max_length=255)),
                ("type", models.CharField(max_length=255)),
                ("status", models.SmallIntegerField(default=1)),
                ("object_id", models.PositiveIntegerField(db_index=True)),
                ("handler_error", models.JSONField(default=None, null=True)),
                (
                    "content_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="contenttypes.contenttype"
                    ),
                ),
            ],
        ),
    ]
