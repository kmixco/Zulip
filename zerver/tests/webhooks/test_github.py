import ujson
from six import text_type
from typing import Dict, Optional

from zerver.models import Message
from zerver.lib.webhooks.git import COMMITS_LIMIT
from zerver.lib.test_helpers import WebhookTestCase

class GithubV1HookTests(WebhookTestCase):
    STREAM_NAME = None # type: Optional[text_type]
    URL_TEMPLATE = u"/api/v1/external/github"
    FIXTURE_DIR_NAME = 'github'
    SEND_STREAM = False
    BRANCHES = None # type: Optional[text_type]

    push_content = u"""zbenjamin [pushed](https://github.com/zbenjamin/zulip-test/compare/4f9adc4777d5...b95449196980) to branch master

* [48c329a](https://github.com/zbenjamin/zulip-test/commit/48c329a0b68a9a379ff195ee3f1c1f4ab0b2a89e): Add baz
* [06ebe5f](https://github.com/zbenjamin/zulip-test/commit/06ebe5f472a32f6f31fd2a665f0c7442b69cce72): Baz needs to be longer
* [b954491](https://github.com/zbenjamin/zulip-test/commit/b95449196980507f08209bdfdc4f1d611689b7a8): Final edit to baz, I swear"""

    def test_spam_branch_is_ignored(self):
        # type: () -> None
        self.SEND_STREAM = True
        self.STREAM_NAME = 'commits'
        self.BRANCHES = 'dev,staging'
        data = self.get_body('push')

        # We subscribe to the stream in this test, even though
        # it won't get written, to avoid failing for the wrong
        # reason.
        self.subscribe_to_stream(self.TEST_USER_EMAIL, self.STREAM_NAME)

        prior_count = Message.objects.count()

        result = self.client_post(self.URL_TEMPLATE, data)
        self.assert_json_success(result)

        after_count = Message.objects.count()
        self.assertEqual(prior_count, after_count)

    def get_body(self, fixture_name):
        # type: (text_type) -> Dict[str, text_type]
        api_key = self.get_api_key(self.TEST_USER_EMAIL)
        data = ujson.loads(self.fixture_data(self.FIXTURE_DIR_NAME, 'v1_' + fixture_name))
        data.update({'email': self.TEST_USER_EMAIL,
                     'api-key': api_key,
                     'payload': ujson.dumps(data['payload'])})
        if self.SEND_STREAM:
            data['stream'] = self.STREAM_NAME

        if self.BRANCHES is not None:
            data['branches'] = self.BRANCHES
        return data

    def basic_test(self, fixture_name, stream_name, expected_subject, expected_content, send_stream=False, branches=None):
        # type: (text_type, text_type, text_type, text_type, bool, Optional[text_type]) -> None
        self.STREAM_NAME = stream_name
        self.SEND_STREAM = send_stream
        self.BRANCHES = branches
        self.send_and_test_stream_message(fixture_name, expected_subject, expected_content, content_type=None)

    def test_user_specified_branches(self):
        # type: () -> None
        self.basic_test('push', 'my_commits', 'zulip-test / master', self.push_content,
                        send_stream=True, branches="master,staging")

    def test_user_specified_stream(self):
        # type: () -> None
        """Around May 2013 the github webhook started to specify the stream.
        Before then, the stream was hard coded to "commits"."""
        self.basic_test('push', 'my_commits', 'zulip-test / master', self.push_content,
                        send_stream=True)

    def test_legacy_hook(self):
        # type: () -> None
        self.basic_test('push', 'commits', 'zulip-test / master', self.push_content)

    def test_push_multiple_commits(self):
        # type: () -> None
        commit_info = "* [48c329a](https://github.com/zbenjamin/zulip-test/commit/48c329a0b68a9a379ff195ee3f1c1f4ab0b2a89e): Add baz\n"
        expected_subject = "zbenjamin [pushed](https://github.com/zbenjamin/zulip-test/compare/4f9adc4777d5...b95449196980) to branch master\n\n{}[and {} more commit(s)]".format(
            commit_info * COMMITS_LIMIT,
            50 - COMMITS_LIMIT,
        )
        self.basic_test('push_commits_more_than_limit', 'commits', 'zulip-test / master', expected_subject)

    def test_issues_opened(self):
        # type: () -> None
        self.basic_test('issues_opened', 'issues',
                        "zulip-test / Issue #5 The frobnicator doesn't work",
                        "zbenjamin opened [Issue](https://github.com/zbenjamin/zulip-test/issues/5)\n\n~~~ quote\nI tried changing the widgets, but I got:\r\n\r\nPermission denied: widgets are immutable\n~~~")

    def test_issue_comment(self):
        # type: () -> None
        self.basic_test('issue_comment', 'issues',
                        "zulip-test / Issue #5 The frobnicator doesn't work",
                        "zbenjamin [commented](https://github.com/zbenjamin/zulip-test/issues/5#issuecomment-23374280) [Issue](https://github.com/zbenjamin/zulip-test/issues/5)\n\n~~~ quote\nWhoops, I did something wrong.\r\n\r\nI'm sorry.\n~~~")

    def test_issues_closed(self):
        # type: () -> None
        self.basic_test('issues_closed', 'issues',
                        "zulip-test / Issue #5 The frobnicator doesn't work",
                        "zbenjamin closed [Issue](https://github.com/zbenjamin/zulip-test/issues/5)")

    def test_pull_request_opened(self):
        # type: () -> None
        self.basic_test('pull_request_opened', 'commits',
                        "zulip-test / PR #7 Counting is hard.",
                        "lfaraone opened [PR](https://github.com/zbenjamin/zulip-test/pull/7)(assigned to lfaraone)\nfrom `patch-2` to `master`\n\n~~~ quote\nOmitted something I think?\n~~~")

    def test_pull_request_closed(self):
        # type: () -> None
        self.basic_test('pull_request_closed', 'commits',
                        "zulip-test / PR #7 Counting is hard.",
                        "zbenjamin closed [PR](https://github.com/zbenjamin/zulip-test/pull/7)")

    def test_pull_request_synchronize(self):
        # type: () -> None
        self.basic_test('pull_request_synchronize', 'commits',
                        "zulip-test / PR #13 Even more cowbell.",
                        "zbenjamin synchronized [PR](https://github.com/zbenjamin/zulip-test/pull/13)")

    def test_pull_request_comment(self):
        # type: () -> None
        self.basic_test('pull_request_comment', 'commits',
                        "zulip-test / PR #9 Less cowbell.",
                        "zbenjamin [commented](https://github.com/zbenjamin/zulip-test/pull/9#issuecomment-24771110) [PR](https://github.com/zbenjamin/zulip-test/pull/9)\n\n~~~ quote\nYeah, who really needs more cowbell than we already have?\n~~~")

    def test_pull_request_comment_user_specified_stream(self):
        # type: () -> None
        self.basic_test('pull_request_comment', 'my_commits',
                        "zulip-test / PR #9 Less cowbell.",
                        "zbenjamin [commented](https://github.com/zbenjamin/zulip-test/pull/9#issuecomment-24771110) [PR](https://github.com/zbenjamin/zulip-test/pull/9)\n\n~~~ quote\nYeah, who really needs more cowbell than we already have?\n~~~",
                        send_stream=True)

    def test_commit_comment(self):
        # type: () -> None
        self.basic_test('commit_comment', 'commits',
                        "zulip-test: commit 7c994678d2f98797d299abed852d3ff9d0834533",
                        "zbenjamin [commented](https://github.com/zbenjamin/zulip-test/commit/7c994678d2f98797d299abed852d3ff9d0834533#commitcomment-4252302)\n\n~~~ quote\nAre we sure this is enough cowbell?\n~~~")

    def test_commit_comment_line(self):
        # type: () -> None
        self.basic_test('commit_comment_line', 'commits',
                        "zulip-test: commit 7c994678d2f98797d299abed852d3ff9d0834533",
                        "zbenjamin [commented](https://github.com/zbenjamin/zulip-test/commit/7c994678d2f98797d299abed852d3ff9d0834533#commitcomment-4252307) on `cowbell`, line 13\n\n~~~ quote\nThis line adds /unlucky/ cowbell (because of its line number).  We should remove it.\n~~~")

class GithubV2HookTests(WebhookTestCase):
    STREAM_NAME = None # type: Optional[text_type]
    URL_TEMPLATE = u"/api/v1/external/github"
    FIXTURE_DIR_NAME = 'github'
    SEND_STREAM = False
    BRANCHES = None # type: Optional[text_type]

    push_content = """zbenjamin [pushed](https://github.com/zbenjamin/zulip-test/compare/4f9adc4777d5...b95449196980) to branch master

* [48c329a](https://github.com/zbenjamin/zulip-test/commit/48c329a0b68a9a379ff195ee3f1c1f4ab0b2a89e): Add baz
* [06ebe5f](https://github.com/zbenjamin/zulip-test/commit/06ebe5f472a32f6f31fd2a665f0c7442b69cce72): Baz needs to be longer
* [b954491](https://github.com/zbenjamin/zulip-test/commit/b95449196980507f08209bdfdc4f1d611689b7a8): Final edit to baz, I swear"""

    def test_spam_branch_is_ignored(self):
        # type: () -> None
        self.SEND_STREAM = True
        self.STREAM_NAME = 'commits'
        self.BRANCHES = 'dev,staging'
        data = self.get_body('push')

        # We subscribe to the stream in this test, even though
        # it won't get written, to avoid failing for the wrong
        # reason.
        self.subscribe_to_stream(self.TEST_USER_EMAIL, self.STREAM_NAME)

        prior_count = Message.objects.count()

        result = self.client_post(self.URL_TEMPLATE, data)
        self.assert_json_success(result)

        after_count = Message.objects.count()
        self.assertEqual(prior_count, after_count)

    def get_body(self, fixture_name):
        # type: (text_type) -> Dict[str, text_type]
        api_key = self.get_api_key(self.TEST_USER_EMAIL)
        data = ujson.loads(self.fixture_data(self.FIXTURE_DIR_NAME, 'v2_' + fixture_name))
        data.update({'email': self.TEST_USER_EMAIL,
                     'api-key': api_key,
                     'payload': ujson.dumps(data['payload'])})
        if self.SEND_STREAM:
            data['stream'] = self.STREAM_NAME

        if self.BRANCHES is not None:
            data['branches'] = self.BRANCHES
        return data

    def basic_test(self, fixture_name, stream_name, expected_subject, expected_content, send_stream=False, branches=None):
        # type: (text_type, text_type, text_type, text_type, bool, Optional[text_type]) -> None
        self.STREAM_NAME = stream_name
        self.SEND_STREAM = send_stream
        self.BRANCHES = branches
        self.send_and_test_stream_message(fixture_name, expected_subject, expected_content, content_type=None)

    def test_user_specified_branches(self):
        # type: () -> None
        self.basic_test('push', 'my_commits', 'zulip-test / master', self.push_content,
                        send_stream=True, branches="master,staging")

    def test_user_specified_stream(self):
        # type: () -> None
        """Around May 2013 the github webhook started to specify the stream.
        Before then, the stream was hard coded to "commits"."""
        self.basic_test('push', 'my_commits', 'zulip-test / master', self.push_content,
                        send_stream=True)

    def test_push_multiple_commits(self):
        # type: () -> None
        commit_info = "* [48c329a](https://github.com/zbenjamin/zulip-test/commit/48c329a0b68a9a379ff195ee3f1c1f4ab0b2a89e): Add baz\n"
        expected_subject = "zbenjamin [pushed](https://github.com/zbenjamin/zulip-test/compare/4f9adc4777d5...b95449196980) to branch master\n\n{}[and {} more commit(s)]".format(
            commit_info * COMMITS_LIMIT,
            50 - COMMITS_LIMIT,
        )
        self.basic_test('push_commits_more_than_limit', 'commits', 'zulip-test / master', expected_subject)


    def test_legacy_hook(self):
        # type: () -> None
        self.basic_test('push', 'commits', 'zulip-test / master', self.push_content)

    def test_issues_opened(self):
        # type: () -> None
        self.basic_test('issues_opened', 'issues',
                        "zulip-test / Issue #5 The frobnicator doesn't work",
                        "zbenjamin opened [Issue](https://github.com/zbenjamin/zulip-test/issues/5)\n\n~~~ quote\nI tried changing the widgets, but I got:\r\n\r\nPermission denied: widgets are immutable\n~~~")

    def test_issue_comment(self):
        # type: () -> None
        self.basic_test('issue_comment', 'issues',
                        "zulip-test / Issue #5 The frobnicator doesn't work",
                        "zbenjamin [commented](https://github.com/zbenjamin/zulip-test/issues/5#issuecomment-23374280) [Issue](https://github.com/zbenjamin/zulip-test/issues/5)\n\n~~~ quote\nWhoops, I did something wrong.\r\n\r\nI'm sorry.\n~~~")

    def test_issues_closed(self):
        # type: () -> None
        self.basic_test('issues_closed', 'issues',
                        "zulip-test / Issue #5 The frobnicator doesn't work",
                        "zbenjamin closed [Issue](https://github.com/zbenjamin/zulip-test/issues/5)")

    def test_pull_request_opened(self):
        # type: () -> None
        self.basic_test('pull_request_opened', 'commits',
                        "zulip-test / PR #7 Counting is hard.",
                        "lfaraone opened [PR](https://github.com/zbenjamin/zulip-test/pull/7)(assigned to lfaraone)\nfrom `patch-2` to `master`\n\n~~~ quote\nOmitted something I think?\n~~~")

    def test_pull_request_closed(self):
        # type: () -> None
        self.basic_test('pull_request_closed', 'commits',
                        "zulip-test / PR #7 Counting is hard.",
                        "zbenjamin closed [PR](https://github.com/zbenjamin/zulip-test/pull/7)")

    def test_pull_request_synchronize(self):
        # type: () -> None
        self.basic_test('pull_request_synchronize', 'commits',
                        "zulip-test / PR #13 Even more cowbell.",

                        "zbenjamin synchronized [PR](https://github.com/zbenjamin/zulip-test/pull/13)")

    def test_pull_request_comment(self):
        # type: () -> None
        self.basic_test('pull_request_comment', 'commits',
                        "zulip-test / PR #9 Less cowbell.",
                        "zbenjamin [commented](https://github.com/zbenjamin/zulip-test/pull/9#issuecomment-24771110) [PR](https://github.com/zbenjamin/zulip-test/pull/9)\n\n~~~ quote\nYeah, who really needs more cowbell than we already have?\n~~~")

    def test_pull_request_comment_user_specified_stream(self):
        # type: () -> None
        self.basic_test('pull_request_comment', 'my_commits',
                        "zulip-test / PR #9 Less cowbell.",
                        "zbenjamin [commented](https://github.com/zbenjamin/zulip-test/pull/9#issuecomment-24771110) [PR](https://github.com/zbenjamin/zulip-test/pull/9)\n\n~~~ quote\nYeah, who really needs more cowbell than we already have?\n~~~",
                        send_stream=True)

    def test_commit_comment(self):
        # type: () -> None
        self.basic_test('commit_comment', 'commits',
                        "zulip-test: commit 7c994678d2f98797d299abed852d3ff9d0834533",
                        "zbenjamin [commented](https://github.com/zbenjamin/zulip-test/commit/7c994678d2f98797d299abed852d3ff9d0834533#commitcomment-4252302)\n\n~~~ quote\nAre we sure this is enough cowbell?\n~~~")

    def test_commit_comment_line(self):
        # type: () -> None
        self.basic_test('commit_comment_line', 'commits',
                        "zulip-test: commit 7c994678d2f98797d299abed852d3ff9d0834533",
                        "zbenjamin [commented](https://github.com/zbenjamin/zulip-test/commit/7c994678d2f98797d299abed852d3ff9d0834533#commitcomment-4252307) on `cowbell`, line 13\n\n~~~ quote\nThis line adds /unlucky/ cowbell (because of its line number).  We should remove it.\n~~~")
