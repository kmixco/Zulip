#!/usr/bin/env python

from __future__ import absolute_import
from __future__ import print_function

import os
import sys

our_dir = os.path.dirname(os.path.abspath(__file__))
# For dev setups, we can find the API in the repo itself.
if os.path.exists(os.path.join(our_dir, '..')):
    sys.path.insert(0, '..')
from bots_test_lib import BotTestCase

class TestDefineBot(BotTestCase):
    bot_name = "define"

    def test_bot(self):
        expected = { "":    'Please enter a word to define.',
                     "foo": "**foo**:\nDefinition not available.",
                     "cat": 
            ("**cat**:\n\n* (**noun**) a small domesticated carnivorous mammal "
             "with soft fur, a short snout, and retractile claws. It is widely "
             "kept as a pet or for catching mice, and many breeds have been "
             "developed.\n&nbsp;&nbsp;their pet cat\n\n"),
                   }
        for m, r in expected.items():
            self.assert_bot_output(
                {'content': m, 'type': "private", 'sender_email': "foo"}, r)
            self.assert_bot_output(
                {'content': m, 'type': "stream", 'display_recipient': "foo", 
                 'subject': "foo"}, r)
