"""
The contents of this file are taken from
[Django-admin](https://github.com/niwinz/django-jinja/blob/master/django_jinja/management/commands/makemessages.py)

Jinja2's i18n functionality is not exactly the same as Django's.
In particular, the tags names and their syntax are different:

  1. The Django ``trans`` tag is replaced by a _() global.
  2. The Django ``blocktrans`` tag is called ``trans``.

(1) isn't an issue, since the whole ``makemessages`` process is based on
converting the template tags to ``_()`` calls. However, (2) means that
those Jinja2 ``trans`` tags will not be picked up by Django's
``makemessages`` command.

There aren't any nice solutions here. While Jinja2's i18n extension does
come with extraction capabilities built in, the code behind ``makemessages``
unfortunately isn't extensible, so we can:

  * Duplicate the command + code behind it.
  * Offer a separate command for Jinja2 extraction.
  * Try to get Django to offer hooks into makemessages().
  * Monkey-patch.

We are currently doing that last thing. It turns out there we are lucky
for once: It's simply a matter of extending two regular expressions.
Credit for the approach goes to:
http://stackoverflow.com/questions/2090717/getting-translation-strings-for-jinja2-templates-integrated-with-django-1-x

"""
from __future__ import absolute_import

import os
import re
import glob
import ujson
from six.moves import filter
from six.moves import map
from six.moves import zip

from django.core.management.commands import makemessages
from django.utils.translation import trans_real
from django.template.base import BLOCK_TAG_START, BLOCK_TAG_END

strip_whitespace_right = re.compile(r"(%s-?\s*(trans|pluralize).*?-%s)\s+" % (BLOCK_TAG_START, BLOCK_TAG_END), re.U)
strip_whitespace_left = re.compile(r"\s+(%s-\s*(endtrans|pluralize).*?-?%s)" % (BLOCK_TAG_START, BLOCK_TAG_END), re.U)

regexes = ['{{#tr .*?}}(.*?){{/tr}}',
           '{{t "(.*?)"\W*}}',
           "{{t '(.*?)'\W*}}",
           ]

frontend_compiled_regexes = [re.compile(regex) for regex in regexes]

def strip_whitespaces(src):
    src = strip_whitespace_left.sub(r'\1', src)
    src = strip_whitespace_right.sub(r'\1', src)
    return src

class Command(makemessages.Command):

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('--frontend-source', type=str,
                            default='static/templates',
                            help='Name of the Handlebars template directory')
        parser.add_argument('--frontend-output', type=str,
                            default='static/locale',
                            help='Name of the frontend messages output directory')
        parser.add_argument('--frontend-namespace', type=str,
                            default='translations.json',
                            help='Namespace of the frontend locale file')

    def handle(self, *args, **options):
        self.handle_django_locales(*args, **options)
        self.handle_frontend_locales(*args, **options)

    def handle_frontend_locales(self, *args, **options):
        self.frontend_source = options.get('frontend_source')
        self.frontend_output = options.get('frontend_output')
        self.frontend_namespace = options.get('frontend_namespace')
        self.frontend_locale = options.get('locale')
        self.frontend_exclude = options.get('exclude')
        self.frontend_all = options.get('all')

        translation_strings = self.get_translation_strings()
        self.write_translation_strings(translation_strings)

    def handle_django_locales(self, *args, **options):
        old_endblock_re = trans_real.endblock_re
        old_block_re = trans_real.block_re
        old_constant_re = trans_real.constant_re

        old_templatize = trans_real.templatize
        # Extend the regular expressions that are used to detect
        # translation blocks with an "OR jinja-syntax" clause.
        trans_real.endblock_re = re.compile(
            trans_real.endblock_re.pattern + '|' + r"""^-?\s*endtrans\s*-?$""")
        trans_real.block_re = re.compile(
            trans_real.block_re.pattern + '|' + r"""^-?\s*trans(?:\s+(?!'|")(?=.*?=.*?)|\s*-?$)""")
        trans_real.plural_re = re.compile(
            trans_real.plural_re.pattern + '|' + r"""^-?\s*pluralize(?:\s+.+|-?$)""")
        trans_real.constant_re = re.compile(r"""_\(((?:".*?")|(?:'.*?')).*\)""")

        def my_templatize(src, origin=None):
            new_src = strip_whitespaces(src)
            return old_templatize(new_src, origin)

        trans_real.templatize = my_templatize

        try:
            super(Command, self).handle(*args, **options)
        finally:
            trans_real.endblock_re = old_endblock_re
            trans_real.block_re = old_block_re
            trans_real.templatize = old_templatize
            trans_real.constant_re = old_constant_re

    def extract_strings(self, data):
        translation_strings = {}
        for regex in frontend_compiled_regexes:
            for match in regex.findall(data):
                translation_strings[match] = ""

        return translation_strings

    def get_translation_strings(self):
        translation_strings = {}
        dirname = self.get_template_dir()

        for filename in os.listdir(dirname):
            if filename.endswith('handlebars'):
                with open(os.path.join(dirname, filename)) as reader:
                    data = reader.read()
                    translation_strings.update(self.extract_strings(data))

        return translation_strings

    def get_template_dir(self):
        return self.frontend_source


    def get_namespace(self):
        return self.frontend_namespace

    def get_locales(self):
        locale = self.frontend_locale
        exclude = self.frontend_exclude
        process_all = self.frontend_all

        paths = glob.glob('%s/*' % self.default_locale_path,)
        locale_dirs = list(filter(os.path.isdir, paths))
        all_locales = list(map(os.path.basename, locale_dirs))

        # Account for excluded locales
        if process_all:
            locales = all_locales
        else:
            locales = locale or all_locales
            locales = set(locales) - set(exclude)

        return locales

    def get_base_path(self):
        return self.frontend_output

    def get_output_paths(self):
        base_path = self.get_base_path()
        locales = self.get_locales()
        for path in [os.path.join(base_path, locale) for locale in locales]:
            if not os.path.exists(path):
                os.makedirs(path)

            yield os.path.join(path, self.get_namespace())

    def get_new_strings(self, old_strings, translation_strings):
        """
        Missing strings are removed, new strings are added and already
        translated strings are not touched.
        """
        new_strings = {}
        for k in translation_strings:
            new_strings[k] = old_strings.get(k, k)

        return new_strings

    def write_translation_strings(self, translation_strings):
        for locale, output_path in zip(self.get_locales(), self.get_output_paths()):
            self.stdout.write("[frontend] processing locale {}".format(locale))
            try:
                with open(output_path, 'r') as reader:
                    old_strings = ujson.load(reader)
            except (IOError, ValueError):
                old_strings = {}

            new_strings = self.get_new_strings(old_strings, translation_strings)
            with open(output_path, 'w') as writer:
                ujson.dump(new_strings, writer)
