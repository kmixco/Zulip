#!/usr/bin/env python3
import os
import errno

from premailer import Premailer
from cssutils import profile
from cssutils.profiles import Profiles, properties, macros

ZULIP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../')

def configure_cssutils() -> None:
    # These properties are not supported by cssutils by default and will
    # result in warnings when premailer package is run.
    properties[Profiles.CSS_LEVEL_2]['-ms-interpolation-mode'] = r'none|bicubic|nearest-neighbor'
    properties[Profiles.CSS_LEVEL_2]['-ms-text-size-adjust'] = r'none|auto|{percentage}'
    properties[Profiles.CSS_LEVEL_2]['mso-table-lspace'] = r'0|{num}(pt)'
    properties[Profiles.CSS_LEVEL_2]['mso-table-rspace'] = r'0|{num}(pt)'
    properties[Profiles.CSS_LEVEL_2]['-webkit-text-size-adjust'] = r'none|auto|{percentage}'
    properties[Profiles.CSS_LEVEL_2]['mso-hide'] = 'all'
    properties[Profiles.CSS_LEVEL_2]['pointer-events'] = (r'auto|none|visiblePainted|'
                                                          r'visibleFill|visibleStroke|'
                                                          r'visible|painted|fill|stroke|all|inherit')

    profile.addProfiles([(Profiles.CSS_LEVEL_2, properties[Profiles.CSS_LEVEL_2],
                         macros[Profiles.CSS_LEVEL_2])])

def escape_jinja2_characters(text: str) -> str:
    escaped_jinja2_characters = [('%7B%7B%20', '{{ '), ('%20%7D%7D', ' }}'), ('&gt;', '>')]
    for escaped, original in escaped_jinja2_characters:
        text = text.replace(escaped, original)
    return text

def strip_unnecesary_tags(text: str) -> str:
    end_block = '</body>\n</html>'
    start_block = '{% extends'
    start = text.find(start_block)
    end = text.rfind(end_block)
    if start != -1 and end != -1:
        text = text[start:end]
        return text
    else:
        raise ValueError("Template does not have %s or %s" % (start_block, end_block))

if __name__ == "__main__":
    templates_to_inline = set()
    for f in os.listdir(os.path.join(ZULIP_PATH, 'templates', 'zerver', 'emails')):
        if f.endswith('.source.html'):
            templates_to_inline.add(f.split('.source.html')[0])

    configure_cssutils()

    os.chdir(os.path.join(ZULIP_PATH, 'templates', 'zerver', 'emails'))

    try:
        os.makedirs("compiled")
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    for template in templates_to_inline:
        template_html_source = template + ".source.html"
        compiled_template_path = os.path.join(os.getcwd(), "compiled", template + ".html")

        with open(template_html_source) as template_source_file:
            template_str = template_source_file.read()
        output = Premailer(template_str,
                           external_styles=["email.css"]).transform()

        output = escape_jinja2_characters(output)

        # Premailer.transform will try to complete the DOM tree,
        # adding html, head, and body tags if they aren't there.
        # While this is correct for the email_base_default template,
        # it is wrong for the other templates that extend this
        # template, since we'll end up with 2 copipes of those tags.
        # Thus, we strip this stuff out if the template extends
        # another template.
        if template != 'email_base_default':
            output = strip_unnecesary_tags(output)

        if ('zerver/emails/compiled/email_base_default.html' in output or
                'zerver/emails/email_base_messages.html' in output):
            assert output.count('<html>') == 0
            assert output.count('<body>') == 0
            assert output.count('</html>') == 0
            assert output.count('</body>') == 0

        with open(compiled_template_path, 'w') as final_template_file:
            final_template_file.write(output)
