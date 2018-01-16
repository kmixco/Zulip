# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-06-18 21:26

import os

import ujson
from django.conf import settings
from django.db import migrations, models
from django.db.backends.postgresql_psycopg2.schema import DatabaseSchemaEditor
from django.db.migrations.state import StateApps

def populate_new_fields(apps: StateApps, schema_editor: DatabaseSchemaEditor) -> None:
    # Open the JSON file which contains the data to be used for migration.
    MIGRATION_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "management", "data")
    path_to_unified_reactions = os.path.join(MIGRATION_DATA_PATH, "unified_reactions.json")
    unified_reactions = ujson.load(open(path_to_unified_reactions))

    Reaction = apps.get_model('zerver', 'Reaction')
    for reaction in Reaction.objects.all():
        reaction.emoji_code = unified_reactions.get(reaction.emoji_name)
        if reaction.emoji_code is None:
            # If it's not present in the unified_reactions map, it's a realm emoji.
            reaction.emoji_code = reaction.emoji_name
            if reaction.emoji_name == 'zulip':
                # `:zulip:` emoji is a zulip special custom emoji.
                reaction.reaction_type = 'zulip_extra_emoji'
            else:
                reaction.reaction_type = 'realm_emoji'
        reaction.save()

class Migration(migrations.Migration):

    dependencies = [
        ('zerver', '0096_add_password_required'),
    ]

    operations = [
        migrations.AddField(
            model_name='reaction',
            name='emoji_code',
            field=models.TextField(default='unset'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='reaction',
            name='reaction_type',
            field=models.CharField(choices=[('unicode_emoji', 'Unicode emoji'), ('realm_emoji', 'Realm emoji'), ('zulip_extra_emoji', 'Zulip extra emoji')], default='unicode_emoji', max_length=30),
        ),
        migrations.RunPython(populate_new_fields,
                             reverse_code=migrations.RunPython.noop),
    ]
