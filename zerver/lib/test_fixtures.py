# -*- coding: utf-8 -*-
import os
import re
import hashlib
from typing import Any, Optional
from importlib import import_module
from six import text_type
from six.moves import cStringIO as StringIO

from django.db import connections, DEFAULT_DB_ALIAS
from django.apps import apps
from django.core.management import call_command
from django.utils.module_loading import module_has_submodule

def database_exists(database_name, **options):
    # type: (text_type, **Any) -> bool
    db = options.get('database', DEFAULT_DB_ALIAS)
    connection = connections[db]

    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 from pg_database WHERE datname='{}';".format(database_name))
        return_value = bool(cursor.fetchone())
    connections.close_all()
    return return_value

def get_migration_status(**options):
    # type: (**Any) -> str
    verbosity = options.get('verbosity', 1)

    for app_config in apps.get_app_configs():
        if module_has_submodule(app_config.module, "management"):
            import_module('.management', app_config.name)

    app_labels = [options['app_label']] if options.get('app_label') else None
    db = options.get('database', DEFAULT_DB_ALIAS)
    out = StringIO()
    call_command(
        'showmigrations',
        '--list',
        app_labels=app_labels,
        database=db,
        no_color=options.get('no_color', False),
        settings=options.get('settings', os.environ['DJANGO_SETTINGS_MODULE']),
        stdout=out,
        traceback=options.get('traceback', True),
        verbosity=verbosity,
    )
    connections.close_all()
    out.seek(0)
    output = out.read()
    return re.sub('\x1b\[(1|0)m', '', output)

def are_migrations_the_same(migration_file, **options):
    # type: (text_type, **Any) -> bool
    if not os.path.exists(migration_file):
        return False

    with open(migration_file) as f:
        migration_content = f.read()
    return migration_content == get_migration_status(**options)

def _check_hash(source_hash_file, target_hash_file, **options):
    # type: (text_type, text_type, **Any) -> bool
    """
    This function has a side effect of creating a new hash file or
    updating the old hash file.
    """
    with open(target_hash_file) as f:
        target_hash_content = hashlib.sha1(f.read().encode('utf8')).hexdigest()

    with open(source_hash_file, 'a+') as f:
        source_hash_content = f.read().strip()
        f.truncate(0)
        f.write(target_hash_content)
        return source_hash_content == target_hash_content

def populate_db_hash_is_same(hash_file, **options):
    # type: (text_type, **Any) -> bool
    populate_db = 'zilencer/management/commands/populate_db.py'
    return _check_hash(hash_file, populate_db, **options)

def postgres_init_test_db_hash_is_same(hash_file, **options):
    # type: (text_type, **Any) -> bool
    postgres_init_test_db = 'tools/setup/postgres-init-test-db'
    return _check_hash(hash_file, postgres_init_test_db, **options)

def is_template_database_current(
        database_name='zulip_test_template',
        migration_status='var/migration-status',
        settings='zproject.test_settings',
        populate_db_hash='var/populate_db_hash',
        postgres_init_test_db_hash='var/postgres_init_test_db_hash'
    ):
    # type: (Optional[text_type], Optional[text_type], Optional[text_type], Optional[text_type], Optional[text_type]) -> bool
    if database_exists(database_name):
        # Due to the way the processing of Python conditionals takes place, it
        # is possible that all missing hashes are not created in one pass e.g.
        # if `populsate_db_hash_is_same` fails then
        # `populate_init_test_db_hash_is_same` will not run.
        return (
            are_migrations_the_same(migration_status, settings=settings) and
            populate_db_hash_is_same(populate_db_hash) and
            postgres_init_test_db_hash_is_same(postgres_init_test_db_hash)
        )
    return False
