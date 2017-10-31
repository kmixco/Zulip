import lxml

from lxml.html.diff import htmldiff
from typing import Optional

def highlight_with_class(text, klass):
    # type: (str, str) -> str
    return '<span class="%s">%s</span>' % (klass, text)

def highlight_html_differences(s1, s2, msg_id=None):
    # type: (str, str, Optional[int]) -> str
    retval = htmldiff(s1, s2)
    fragment = lxml.html.fromstring(retval)  # type: ignore # https://github.com/python/typeshed/issues/525

    for elem in fragment.cssselect('del'):
        elem.tag = 'span'
        elem.set('class', 'highlight_text_deleted')

    for elem in fragment.cssselect('ins'):
        elem.tag = 'span'
        elem.set('class', 'highlight_text_inserted')

    retval = lxml.html.tostring(fragment)   # type: ignore # https://github.com/python/typeshed/issues/525

    return retval
