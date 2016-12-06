# -*- coding: utf-8 -*-
from typing import Text
from zerver.lib.test_classes import WebhookTestCase

class StashHookTests(WebhookTestCase):
    STREAM_NAME = 'stash'
    URL_TEMPLATE = u"/api/v1/external/stash?stream={stream}"

    def test_stash_message(self):
        # type: () -> None
        """
        Messages are generated by Stash on a `git push`.

        The subject describes the repo and Stash "project". The
        content describes the commits pushed.
        """
        expected_subject = u"Secret project/Operation unicorn: master"
        expected_message = """`f259e90` was pushed to **master** in **Secret project/Operation unicorn** with:

* `f259e90`: Updating poms ..."""
        self.send_and_test_stream_message('push', expected_subject, expected_message,
                                          content_type="application/x-www-form-urlencoded",
                                          **self.api_auth(self.TEST_USER_EMAIL))

    def get_body(self, fixture_name):
        # type: (Text) -> Text
        return self.fixture_data("stash", fixture_name, file_type="json")
