# -*- coding: utf-8 -*-

import ujson

from collections import defaultdict
from django.conf import settings
from django.db import migrations, models
from django.db.backends.postgresql_psycopg2.schema import DatabaseSchemaEditor
from django.db.migrations.state import StateApps
from typing import Any, Dict

def realm_emoji_name_to_id(apps: StateApps, schema_editor: DatabaseSchemaEditor) -> None:
    Reaction = apps.get_model('zerver', 'Reaction')
    RealmEmoji = apps.get_model('zerver', 'RealmEmoji')
    realm_emoji_by_realm_id = defaultdict(dict)   # type: Dict[int, Dict[str, Any]]
    for realm_emoji in RealmEmoji.objects.all():
        realm_emoji_by_realm_id[realm_emoji.realm_id] = {
            'id': str(realm_emoji.id),
            'name': realm_emoji.name,
            'deactivated': realm_emoji.deactivated,
        }
    for reaction in Reaction.objects.filter(reaction_type='realm_emoji'):
        realm_id = reaction.user_profile.realm_id
        emoji_name = reaction.emoji_name
        if realm_id in realm_emoji_by_realm_id:
            realm_emoji = realm_emoji_by_realm_id[realm_id].get(emoji_name)
            if realm_emoji is None:
                # Realm emoji used in this reaction has been deleted so this
                # reaction should also be deleted. We don't need to reverse
                # this step in migration reversal code.
                reaction.delete()
            else:
                reaction.emoji_code = realm_emoji["id"]
                reaction.save()

def reversal(apps: StateApps, schema_editor: DatabaseSchemaEditor) -> None:
    Reaction = apps.get_model('zerver', 'Reaction')
    for reaction in Reaction.objects.filter(reaction_type='realm_emoji'):
        reaction.emoji_code = reaction.emoji_name
        reaction.save()

class Migration(migrations.Migration):

    dependencies = [
        ('zerver', '0142_userprofile_translate_emoticons'),
    ]

    operations = [
        migrations.RunPython(realm_emoji_name_to_id,
                             reverse_code=reversal),
    ]
