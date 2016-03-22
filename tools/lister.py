#!/usr/bin/env python
from __future__ import print_function

import os
import sys
import subprocess
import re
from collections import defaultdict

def get_ftype(fpath, use_shebang):
    ext = os.path.splitext(fpath)[1]
    if ext:
        return ext[1:]
    elif use_shebang:
        # opening a file may throw an OSError
        with open(fpath) as f:
            first_line = f.readline()
            if re.search(r'^#!.*\bpython', first_line):
                return 'py'
            elif re.search(r'^#!.*sh', first_line):
                return 'sh'
            elif re.search(r'^#!.*\bperl', first_line):
                return 'pl'
            elif re.search(r'^#!', first_line):
                print('Error: Unknown shebang in file "%s":\n%s' % (fpath, first_line), file=sys.stderr)
                return ''
            else:
                return ''
    else:
        return ''

def list_files(targets=[], ftypes=[], use_shebang=True, modified_only=False,
               exclude=[], group_by_ftype=False):
    """
    List files tracked by git.
    Returns a list of files which are either in targets or in directories in targets.
    If targets is [], list of all tracked files in current directory is returned.

    Other arguments:
    ftypes - List of file types on which to filter the search.
        If ftypes is [], all files are included.
    use_shebang - Determine file type of extensionless files from their shebang.
    modified_only - Only include files which have been modified.
    exclude - List of paths to be excluded.
    group_by_ftype - If True, returns a dict of lists keyed by file type.
        If False, returns a flat list of files.
    """
    ftypes = [x.strip('.') for x in ftypes]
    ftypes_set = set(ftypes)

    cmdline = ['git', 'ls-files'] + targets
    if modified_only:
        cmdline.append('-m')

    files_gen = (x.strip() for x in subprocess.check_output(cmdline, universal_newlines=True).split('\n'))
    # throw away empty lines and non-files (like symlinks)
    files = list(filter(os.path.isfile, files_gen))

    result = defaultdict(list) if group_by_ftype else []

    for fpath in files:
        # this will take a long time if exclude is very large
        in_exclude = False
        for expath in exclude:
            expath = expath.rstrip('/')
            if fpath == expath or fpath.startswith(expath + '/'):
                in_exclude = True
        if in_exclude:
            continue

        if ftypes or group_by_ftype:
            try:
                filetype = get_ftype(fpath, use_shebang)
            except (OSError, UnicodeDecodeError) as e:
                etype = e.__class__.__name__
                print('Error: %s while determining type of file "%s":' % (etype, fpath), file=sys.stderr)
                print(e, file=sys.stderr)
                filetype = ''
            if ftypes and filetype not in ftypes_set:
                continue

        if group_by_ftype:
            result['.' + filetype].append(fpath)
        else:
            result.append(fpath)

    return result
