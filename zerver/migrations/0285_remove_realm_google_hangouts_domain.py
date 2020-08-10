# Generated by Django 2.2.13 on 2020-06-14 01:58

from django.db import migrations
from django.db.backends.postgresql.schema import DatabaseSchemaEditor
from django.db.migrations.state import StateApps

VIDEO_CHAT_PROVIDERS = {
    'jitsi_meet': {
        'name': "Jitsi Meet",
        'id': 1,
    },
    'google_hangouts': {
        'name': "Google Hangouts",
        'id': 2,
    },
}

def remove_google_hangouts_provider(apps: StateApps, schema_editor: DatabaseSchemaEditor) -> None:
    # We are removing the Google Hangout integration because Google has
    # removed the Hangouts brand. All the realms that used Hangouts as
    # their video chat provided are now set to the default, jitsi.
    Realm = apps.get_model('zerver', 'Realm')
    Realm.objects.filter(video_chat_provider=VIDEO_CHAT_PROVIDERS['google_hangouts']['id']).update(
        video_chat_provider=VIDEO_CHAT_PROVIDERS['jitsi_meet']['id']
    )

class Migration(migrations.Migration):

    dependencies = [
        ('zerver', '0284_convert_realm_admins_to_realm_owners'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='realm',
            name='google_hangouts_domain',
        ),
        migrations.RunPython(
            remove_google_hangouts_provider,
            reverse_code=migrations.RunPython.noop,
            elidable=True
        ),
    ]
