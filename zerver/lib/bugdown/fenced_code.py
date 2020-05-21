"""
Fenced Code Extension for Python Markdown
=========================================

This extension adds Fenced Code Blocks to Python-Markdown.

    >>> import markdown
    >>> text = '''
    ... A paragraph before a fenced code block:
    ...
    ... ~~~
    ... Fenced code block
    ... ~~~
    ... '''
    >>> html = markdown.markdown(text, extensions=['fenced_code'])
    >>> print html
    <p>A paragraph before a fenced code block:</p>
    <pre><code>Fenced code block
    </code></pre>

Works with safe_mode also (we check this because we are using the HtmlStash):

    >>> print markdown.markdown(text, extensions=['fenced_code'], safe_mode='replace')
    <p>A paragraph before a fenced code block:</p>
    <pre><code>Fenced code block
    </code></pre>

Include tilde's in a code block and wrap with blank lines:

    >>> text = '''
    ... ~~~~~~~~
    ...
    ... ~~~~
    ... ~~~~~~~~'''
    >>> print markdown.markdown(text, extensions=['fenced_code'])
    <pre><code>
    ~~~~
    </code></pre>

Removes trailing whitespace from code blocks that cause horizontal scrolling
    >>> import markdown
    >>> text = '''
    ... A paragraph before a fenced code block:
    ...
    ... ~~~
    ... Fenced code block    \t\t\t\t\t\t\t
    ... ~~~
    ... '''
    >>> html = markdown.markdown(text, extensions=['fenced_code'])
    >>> print html
    <p>A paragraph before a fenced code block:</p>
    <pre><code>Fenced code block
    </code></pre>

Language tags:

    >>> text = '''
    ... ~~~~{.python}
    ... # Some python code
    ... ~~~~'''
    >>> print markdown.markdown(text, extensions=['fenced_code'])
    <pre><code class="python"># Some python code
    </code></pre>

Copyright 2007-2008 [Waylan Limberg](http://achinghead.com/).

Project website: <http://packages.python.org/Markdown/extensions/fenced_code_blocks.html>
Contact: markdown@freewisdom.org

License: BSD (see ../docs/LICENSE for details)

Dependencies:
* [Python 2.4+](http://python.org)
* [Markdown 2.0+](http://packages.python.org/Markdown/)
* [Pygments (optional)](http://pygments.org)

"""

import re
import markdown
from django.utils.html import escape
from markdown.extensions.codehilite import CodeHilite, CodeHiliteExtension
from zerver.lib.exceptions import BugdownRenderingException
from zerver.lib.tex import render_tex
from typing import Any, Dict, Iterable, List, MutableSequence, Optional

# Global vars
FENCE_RE = re.compile("""
    # ~~~ or ```
    (?P<fence>
        ^(?:~{3,}|`{3,})
    )

    [ ]* # spaces

    (
        \\{?\\.?
        (?P<lang>
            [a-zA-Z0-9_+-./#]*
        ) # "py" or "javascript"
        \\}?
    ) # language, like ".py" or "{javascript}"
    [ ]* # spaces
    $
    """, re.VERBOSE)


CODE_WRAP = '<pre><code%s>%s\n</code></pre>'
LANG_TAG = ' class="%s"'

def validate_curl_content(lines: List[str]) -> None:
    error_msg = """
Missing required -X argument in curl command:

{command}
""".strip()

    for line in lines:
        regex = r'curl [-](sS)?X "?(GET|DELETE|PATCH|POST)"?'
        if line.startswith('curl'):
            if re.search(regex, line) is None:
                raise BugdownRenderingException(error_msg.format(command=line.strip()))


CODE_VALIDATORS = {
    'curl': validate_curl_content,
}

class FencedCodeExtension(markdown.Extension):
    def __init__(self, config: Optional[Dict[str, Any]]=None) -> None:
        if config is None:
            config = {}
        self.config = {
            'run_content_validators': [
                config.get('run_content_validators', False),
                'Boolean specifying whether to run content validation code in CodeHandler'
            ]
        }

        for key, value in config.items():
            self.setConfig(key, value)

    def extendMarkdown(self, md: markdown.Markdown, md_globals: Dict[str, Any]) -> None:
        """ Add FencedBlockPreprocessor to the Markdown instance. """
        md.registerExtension(self)
        processor = FencedBlockPreprocessor(
            md, run_content_validators=self.config['run_content_validators'][0])
        md.preprocessors.register(processor, 'fenced_code_block', 25)


class BaseHandler:
    def handle_line(self, line: str) -> None:
        raise NotImplementedError()

    def done(self) -> None:
        raise NotImplementedError()

def generic_handler(processor: Any, output: MutableSequence[str],
                    fence: str, lang: str,
                    run_content_validators: Optional[bool]=False,
                    default_language: Optional[str]=None) -> BaseHandler:
    if lang in ('quote', 'quoted'):
        return QuoteHandler(processor, output, fence, default_language)
    elif lang == 'math':
        return TexHandler(processor, output, fence)
    else:
        return CodeHandler(processor, output, fence, lang, run_content_validators)

def check_for_new_fence(processor: Any, output: MutableSequence[str], line: str,
                        run_content_validators: Optional[bool]=False,
                        default_language: Optional[str]=None) -> None:
    m = FENCE_RE.match(line)
    if m:
        fence = m.group('fence')
        lang = m.group('lang')
        if not lang and default_language:
            lang = default_language
        handler = generic_handler(processor, output, fence, lang, run_content_validators, default_language)
        processor.push(handler)
    else:
        output.append(line)

class OuterHandler(BaseHandler):
    def __init__(self, processor: Any, output: MutableSequence[str],
                 run_content_validators: Optional[bool]=False,
                 default_language: Optional[str]=None) -> None:
        self.output = output
        self.processor = processor
        self.run_content_validators = run_content_validators
        self.default_language = default_language

    def handle_line(self, line: str) -> None:
        check_for_new_fence(self.processor, self.output, line,
                            self.run_content_validators, self.default_language)

    def done(self) -> None:
        self.processor.pop()

class CodeHandler(BaseHandler):
    def __init__(self, processor: Any, output: MutableSequence[str],
                 fence: str, lang: str, run_content_validators: Optional[bool]=False) -> None:
        self.processor = processor
        self.output = output
        self.fence = fence
        self.lang = lang
        self.lines: List[str] = []
        self.run_content_validators = run_content_validators

    def handle_line(self, line: str) -> None:
        if line.rstrip() == self.fence:
            self.done()
        else:
            self.lines.append(line.rstrip())

    def done(self) -> None:
        text = '\n'.join(self.lines)

        # run content validators (if any)
        if self.run_content_validators:
            validator = CODE_VALIDATORS.get(self.lang, lambda text: None)
            validator(self.lines)

        text = self.processor.format_code(self.lang, text)
        text = self.processor.placeholder(text)
        processed_lines = text.split('\n')
        self.output.append('')
        self.output.extend(processed_lines)
        self.output.append('')
        self.processor.pop()

class QuoteHandler(BaseHandler):
    def __init__(self, processor: Any, output: MutableSequence[str],
                 fence: str, default_language: Optional[str]=None) -> None:
        self.processor = processor
        self.output = output
        self.fence = fence
        self.lines: List[str] = []
        self.default_language = default_language

    def handle_line(self, line: str) -> None:
        if line.rstrip() == self.fence:
            self.done()
        else:
            check_for_new_fence(self.processor, self.lines, line, default_language=self.default_language)

    def done(self) -> None:
        text = '\n'.join(self.lines)
        text = self.processor.format_quote(text)
        processed_lines = text.split('\n')
        self.output.append('')
        self.output.extend(processed_lines)
        self.output.append('')
        self.processor.pop()

class TexHandler(BaseHandler):
    def __init__(self, processor: Any, output: MutableSequence[str], fence: str) -> None:
        self.processor = processor
        self.output = output
        self.fence = fence
        self.lines: List[str] = []

    def handle_line(self, line: str) -> None:
        if line.rstrip() == self.fence:
            self.done()
        else:
            self.lines.append(line)

    def done(self) -> None:
        text = '\n'.join(self.lines)
        text = self.processor.format_tex(text)
        text = self.processor.placeholder(text)
        processed_lines = text.split('\n')
        self.output.append('')
        self.output.extend(processed_lines)
        self.output.append('')
        self.processor.pop()


class FencedBlockPreprocessor(markdown.preprocessors.Preprocessor):
    def __init__(self, md: markdown.Markdown, run_content_validators: Optional[bool]=False) -> None:
        markdown.preprocessors.Preprocessor.__init__(self, md)

        self.checked_for_codehilite = False
        self.run_content_validators = run_content_validators
        self.codehilite_conf: Dict[str, List[Any]] = {}

    def push(self, handler: BaseHandler) -> None:
        self.handlers.append(handler)

    def pop(self) -> None:
        self.handlers.pop()

    def run(self, lines: Iterable[str]) -> List[str]:
        """ Match and store Fenced Code Blocks in the HtmlStash. """

        output: List[str] = []

        processor = self
        self.handlers: List[BaseHandler] = []

        default_language = None
        try:
            default_language = self.md.zulip_realm.default_code_block_language
        except AttributeError:
            pass
        handler = OuterHandler(processor, output, self.run_content_validators, default_language)
        self.push(handler)

        for line in lines:
            self.handlers[-1].handle_line(line)

        while self.handlers:
            self.handlers[-1].done()

        # This fiddly handling of new lines at the end of our output was done to make
        # existing tests pass.  Bugdown is just kind of funny when it comes to new lines,
        # but we could probably remove this hack.
        if len(output) > 2 and output[-2] != '':
            output.append('')
        return output

    def format_code(self, lang: str, text: str) -> str:
        if lang:
            langclass = LANG_TAG % (lang,)
        else:
            langclass = ''

        # Check for code hilite extension
        if not self.checked_for_codehilite:
            for ext in self.markdown.registeredExtensions:
                if isinstance(ext, CodeHiliteExtension):
                    self.codehilite_conf = ext.config
                    break

            self.checked_for_codehilite = True

        # If config is not empty, then the codehighlite extension
        # is enabled, so we call it to highlite the code
        if self.codehilite_conf:
            highliter = CodeHilite(text,
                                   linenums=self.codehilite_conf['linenums'][0],
                                   guess_lang=self.codehilite_conf['guess_lang'][0],
                                   css_class=self.codehilite_conf['css_class'][0],
                                   style=self.codehilite_conf['pygments_style'][0],
                                   use_pygments=self.codehilite_conf['use_pygments'][0],
                                   lang=(lang or None),
                                   noclasses=self.codehilite_conf['noclasses'][0])

            code = highliter.hilite()
        else:
            code = CODE_WRAP % (langclass, self._escape(text))

        return code

    def format_quote(self, text: str) -> str:
        paragraphs = text.split("\n\n")
        quoted_paragraphs = []
        for paragraph in paragraphs:
            lines = paragraph.split("\n")
            quoted_paragraphs.append("\n".join("> " + line for line in lines if line != ''))
        return "\n\n".join(quoted_paragraphs)

    def format_tex(self, text: str) -> str:
        paragraphs = text.split("\n\n")
        tex_paragraphs = []
        for paragraph in paragraphs:
            html = render_tex(paragraph, is_inline=False)
            if html is not None:
                tex_paragraphs.append(html)
            else:
                tex_paragraphs.append('<span class="tex-error">' +
                                      escape(paragraph) + '</span>')
        return "\n\n".join(tex_paragraphs)

    def placeholder(self, code: str) -> str:
        return self.markdown.htmlStash.store(code)

    def _escape(self, txt: str) -> str:
        """ basic html escaping """
        txt = txt.replace('&', '&amp;')
        txt = txt.replace('<', '&lt;')
        txt = txt.replace('>', '&gt;')
        txt = txt.replace('"', '&quot;')
        return txt


def makeExtension(*args: Any, **kwargs: None) -> FencedCodeExtension:
    return FencedCodeExtension(kwargs)

if __name__ == "__main__":
    import doctest
    doctest.testmod()
