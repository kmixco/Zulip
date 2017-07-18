from __future__ import print_function
from __future__ import absolute_import

import subprocess

from .printer import print_err, colors

from typing import Any, Dict, List

def check_pyflakes(options, by_lang):
    # type: (Any, Dict[str, List[str]]) -> bool
    if len(by_lang['py']) == 0:
        return False
    failed = False
    color = next(colors)
    pyflakes = subprocess.Popen(['pyflakes'] + by_lang['py'],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)

    for ln in iter(pyflakes.stdout.readline, b''):
        if options.full or not (
            b'imported but unused' in ln or
            b'redefinition of unused' in ln or
            # Our ipython startup pythonrc file intentionally imports *
            (b"scripts/lib/pythonrc.py" in ln and
             b" import *' used; unable to detect undefined names" in ln) or
            # Special dev_settings.py import
            b"from .prod_settings_template import *" in ln or
            (b"settings.py" in ln and
             (b"settings import *' used; unable to detect undefined names" in ln or
              b"may be undefined, or defined from star imports" in ln)) or
            (b"zerver/tornado/ioloop_logging.py" in ln and
             b"redefinition of function 'instrument_tornado_ioloop'" in ln) or
            (b"zephyr_mirror_backend.py:" in ln and
             b"redefinition of unused 'simplejson' from line" in ln)):

            print_err('pyflakes', color, ln)
            failed = True
    return failed
