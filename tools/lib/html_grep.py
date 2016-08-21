from __future__ import absolute_import
from __future__ import print_function
from collections import defaultdict
from six.moves import range

from .template_parser import html_branches, Token, HtmlTreeBranch

def show_all_branches(fns):
    # type: (List[str]) -> None
    for fn in fns:
        text = open(fn).read()
        branches = html_branches(text)
        for branch in branches:
            print(branch.text())
        print('---')

class Grepper(object):
    '''
    A Grepper object is optimized to do repeated
    searches of words that can be found in our
    HtmlTreeBranch objects.
    '''

    def __init__(self, fns):
        # type: (List[str]) -> None
        all_branches = [] # type: List[HtmlTreeBranch]

        for fn in fns:
            branches = html_branches(fn)
            all_branches += branches

        self.word_dict = defaultdict(set) # type: Dict[str, Set[HtmlTreeBranch]]
        for b in all_branches:
            for word in b.words:
                self.word_dict[word].add(b)

        self.all_branches = set(all_branches)

    def grep(self, word_set):
        # type: (Set[str]) -> None

        words = list(word_set) # type: List[str]

        if len(words) == 0:
            matches = self.all_branches
        else:
            matches = self.word_dict[words[0]]
            for i in range(1, len(words)):
                matches = matches & self.word_dict[words[i]]

        branches = list(matches)
        branches.sort(key=lambda branch: (branch.fn, branch.line))
        if False:
            for branch in branches:
                print('%s %d' % (branch.fn, branch.line))
                print(branch.staircase_text())
                print('')
        return len(branches)

def grep(fns, words):
    # type: (List[str], Set[str]) -> None
    grepper = Grepper(fns)
    grepper.grep(words)

