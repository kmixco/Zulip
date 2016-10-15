# -*- coding: utf-8 -*-
from six import text_type
from typing import Union
from zerver.lib.webhooks.git import COMMITS_LIMIT
from zerver.lib.test_helpers import WebhookTestCase

class Bitbucket2HookTests(WebhookTestCase):
    STREAM_NAME = 'bitbucket2'
    URL_TEMPLATE = "/api/v1/external/bitbucket2?stream={stream}&api_key={api_key}"
    FIXTURE_DIR_NAME = 'bitbucket'
    EXPECTED_SUBJECT = u"Repository name"
    EXPECTED_SUBJECT_PR_EVENTS = u"Repository name / PR #1 new commit"
    EXPECTED_SUBJECT_BRANCH_EVENTS = u"Repository name / master"

    def test_bitbucket2_on_push_event(self):
        # type: () -> None
        commit_info = u'* [84b96ad](https://bitbucket.org/kolaszek/repository-name/commits/84b96adc644a30fd6465b3d196369d880762afed): first commit'
        expected_message = u"kolaszek [pushed](https://bitbucket.org/kolaszek/repository-name/branch/master) to branch master\n\n{}".format(commit_info)
        self.send_and_test_stream_message('v2_push', self.EXPECTED_SUBJECT_BRANCH_EVENTS, expected_message)

    def test_bitbucket2_on_push_commits_above_limit_event(self):
        # type: () -> None
        number_of_hidden_commits = 50 - COMMITS_LIMIT
        commit_info = '* [84b96ad](https://bitbucket.org/kolaszek/repository-name/commits/84b96adc644a30fd6465b3d196369d880762afed): first commit\n'
        expected_message = u"kolaszek [pushed](https://bitbucket.org/kolaszek/repository-name/branch/master) to branch master\n\n{}[and {} more commit(s)]".format(
            (commit_info * 10),
            number_of_hidden_commits
        )
        self.send_and_test_stream_message('v2_push_commits_above_limit', self.EXPECTED_SUBJECT_BRANCH_EVENTS, expected_message)

    def test_bitbucket2_on_force_push_event(self):
        # type: () -> None
        expected_message = u"kolaszek [force pushed](https://bitbucket.org/kolaszek/repository-name/branch/master) to branch master. Head is now 25f93d22b719e2d678a7ad5ee0ef0d1fcdf39c12"
        self.send_and_test_stream_message('v2_force_push', self.EXPECTED_SUBJECT_BRANCH_EVENTS, expected_message)

    def test_bitbucket2_on_remove_branch_event(self):
        # type: () -> None
        expected_message = u"kolaszek deleted branch master"
        self.send_and_test_stream_message('v2_remove_branch', self.EXPECTED_SUBJECT_BRANCH_EVENTS, expected_message)

    def test_bitbucket2_on_fork_event(self):
        # type: () -> None
        expected_message = u"User Tomasz(login: kolaszek) forked the repository into [kolaszek/repository-name2](https://bitbucket.org/kolaszek/repository-name2)."
        self.send_and_test_stream_message('v2_fork', self.EXPECTED_SUBJECT, expected_message)

    def test_bitbucket2_on_commit_comment_created_event(self):
        # type: () -> None
        expected_message = u"User Tomasz(login: kolaszek) added [comment](https://bitbucket.org/kolaszek/repository-name/commits/32c4ea19aa3af10acd08e419e2c354941a365d74#comment-3354963) to commit."
        self.send_and_test_stream_message('v2_commit_comment_created', self.EXPECTED_SUBJECT, expected_message)

    def test_bitbucket2_on_commit_status_changed_event(self):
        # type: () -> None
        expected_message = u"[System mybuildtool](https://my-build-tool.com/builds/MY-PROJECT/BUILD-777) changed status of https://bitbucket.org/kolaszek/repository-name/9fec847784abb10b2fa567ee63b85bd238955d0e to SUCCESSFUL."
        self.send_and_test_stream_message('v2_commit_status_changed', self.EXPECTED_SUBJECT, expected_message)

    def test_bitbucket2_on_issue_created_event(self):
        # type: () -> None
        expected_message = u"User Tomasz(login: kolaszek) created [an issue](https://bitbucket.org/kolaszek/repository-name/issues/2/bug)"
        self.send_and_test_stream_message('v2_issue_created', self.EXPECTED_SUBJECT, expected_message)

    def test_bitbucket2_on_issue_updated_event(self):
        # type: () -> None
        expected_message = u"User Tomasz(login: kolaszek) updated [an issue](https://bitbucket.org/kolaszek/repository-name/issues/2/bug)"
        self.send_and_test_stream_message('v2_issue_updated', self.EXPECTED_SUBJECT, expected_message)

    def test_bitbucket2_on_issue_commented_event(self):
        # type: () -> None
        expected_message = u"User Tomasz(login: kolaszek) commented [an issue](https://bitbucket.org/kolaszek/repository-name/issues/2/bug)"
        self.send_and_test_stream_message('v2_issue_commented', self.EXPECTED_SUBJECT, expected_message)

    def test_bitbucket2_on_pull_request_created_event(self):
        # type: () -> None
        expected_message = u"kolaszek created [PR](https://bitbucket.org/kolaszek/repository-name/pull-requests/1)(assigned to tkolek)\nfrom `new-branch` to `master`\n\n~~~ quote\ndescription\n~~~"
        kwargs = {
            "HTTP_X_EVENT_KEY": 'pullrequest:created'
        }
        self.send_and_test_stream_message('v2_pull_request_created_or_updated', self.EXPECTED_SUBJECT_PR_EVENTS, expected_message, **kwargs)

    def test_bitbucket2_on_pull_request_updated_event(self):
        # type: () -> None
        expected_message = u"kolaszek updated [PR](https://bitbucket.org/kolaszek/repository-name/pull-requests/1)(assigned to tkolek)\nfrom `new-branch` to `master`\n\n~~~ quote\ndescription\n~~~"
        kwargs = {
            "HTTP_X_EVENT_KEY": 'pullrequest:updated'
        }
        self.send_and_test_stream_message('v2_pull_request_created_or_updated', self.EXPECTED_SUBJECT_PR_EVENTS, expected_message, **kwargs)

    def test_bitbucket2_on_pull_request_approved_event(self):
        # type: () -> None
        expected_message = u"kolaszek approved [PR](https://bitbucket.org/kolaszek/repository-name/pull-requests/1)"
        kwargs = {
            "HTTP_X_EVENT_KEY": 'pullrequest:approved'
        }
        self.send_and_test_stream_message('v2_pull_request_approved_or_unapproved', self.EXPECTED_SUBJECT_PR_EVENTS, expected_message, **kwargs)

    def test_bitbucket2_on_pull_request_unapproved_event(self):
        # type: () -> None
        expected_message = u"kolaszek unapproved [PR](https://bitbucket.org/kolaszek/repository-name/pull-requests/1)"
        kwargs = {
            "HTTP_X_EVENT_KEY": 'pullrequest:unapproved'
        }
        self.send_and_test_stream_message('v2_pull_request_approved_or_unapproved', self.EXPECTED_SUBJECT_PR_EVENTS, expected_message, **kwargs)

    def test_bitbucket2_on_pull_request_declined_event(self):
        # type: () -> None
        expected_message = u"kolaszek rejected [PR](https://bitbucket.org/kolaszek/repository-name/pull-requests/1)"
        kwargs = {
            "HTTP_X_EVENT_KEY": 'pullrequest:rejected'
        }
        self.send_and_test_stream_message('v2_pull_request_merged_or_rejected', self.EXPECTED_SUBJECT_PR_EVENTS, expected_message, **kwargs)

    def test_bitbucket2_on_pull_request_merged_event(self):
        # type: () -> None
        expected_message = u"kolaszek merged [PR](https://bitbucket.org/kolaszek/repository-name/pull-requests/1)"
        kwargs = {
            "HTTP_X_EVENT_KEY": 'pullrequest:merged'
        }
        self.send_and_test_stream_message('v2_pull_request_merged_or_rejected', self.EXPECTED_SUBJECT_PR_EVENTS, expected_message, **kwargs)

    def test_bitbucket2_on_pull_request_comment_created_event(self):
        # type: () -> None
        expected_message = u"User Tomasz(login: kolaszek) created [comment](https://bitbucket.org/kolaszek/repository-name/pull-requests/3/_/diff#comment-20576503 in [\"new commit\" pull request](https://bitbucket.org/kolaszek/repository-name/pull-requests/3)"
        kwargs = {
            "HTTP_X_EVENT_KEY": 'pullrequest:comment_created'
        }
        self.send_and_test_stream_message('v2_pull_request_comment_action', self.EXPECTED_SUBJECT_PR_EVENTS, expected_message, **kwargs)

    def test_bitbucket2_on_pull_request_comment_updated_event(self):
        # type: () -> None
        expected_message = u"User Tomasz(login: kolaszek) updated [comment](https://bitbucket.org/kolaszek/repository-name/pull-requests/3/_/diff#comment-20576503 in [\"new commit\" pull request](https://bitbucket.org/kolaszek/repository-name/pull-requests/3)"
        kwargs = {
            "HTTP_X_EVENT_KEY": 'pullrequest:comment_updated'
        }
        self.send_and_test_stream_message('v2_pull_request_comment_action', self.EXPECTED_SUBJECT_PR_EVENTS, expected_message, **kwargs)

    def test_bitbucket2_on_pull_request_comment_deleted_event(self):
        # type: () -> None
        expected_message = u"User Tomasz(login: kolaszek) deleted [comment](https://bitbucket.org/kolaszek/repository-name/pull-requests/3/_/diff#comment-20576503 in [\"new commit\" pull request](https://bitbucket.org/kolaszek/repository-name/pull-requests/3)"
        kwargs = {
            "HTTP_X_EVENT_KEY": 'pullrequest:comment_deleted'
        }
        self.send_and_test_stream_message('v2_pull_request_comment_action', self.EXPECTED_SUBJECT_PR_EVENTS, expected_message, **kwargs)

class BitbucketHookTests(WebhookTestCase):
    STREAM_NAME = 'bitbucket'
    URL_TEMPLATE = "/api/v1/external/bitbucket?payload={payload}&stream={stream}"
    FIXTURE_DIR_NAME = 'bitbucket'
    EXPECTED_SUBJECT = u"Repository name"
    EXPECTED_SUBJECT_BRANCH_EVENTS = u"Repository name / master"

    def test_bitbucket_on_push_event(self):
        # type: () -> None
        fixture_name = 'push'
        self.url = self.build_url(fixture_name)
        commit_info = u'* [25f93d2](https://bitbucket.org/kolaszek/repository-name/commits/25f93d22b719e2d678a7ad5ee0ef0d1fcdf39c12): c'
        expected_message = u"kolaszek pushed to branch master\n\n{}".format(commit_info)
        self.send_and_test_stream_message(fixture_name, self.EXPECTED_SUBJECT_BRANCH_EVENTS, expected_message, **self.api_auth(self.TEST_USER_EMAIL))

    def test_bitbucket_on_push_commits_above_limit_event(self):
        # type: () -> None
        fixture_name = 'push_commits_above_limit'
        self.url = self.build_url(fixture_name)
        commit_info = u'* [25f93d2](https://bitbucket.org/kolaszek/repository-name/commits/25f93d22b719e2d678a7ad5ee0ef0d1fcdf39c12): c\n'
        expected_message = u"kolaszek pushed to branch master\n\n{}[and 40 more commit(s)]".format(commit_info * 10)
        self.send_and_test_stream_message(fixture_name, self.EXPECTED_SUBJECT_BRANCH_EVENTS, expected_message, **self.api_auth(self.TEST_USER_EMAIL))

    def test_bitbucket_on_force_push_event(self):
        # type: () -> None
        fixture_name = 'force_push'
        self.url = self.build_url(fixture_name)
        expected_message = u"kolaszek [force pushed](https://bitbucket.org/kolaszek/repository-name)"
        self.send_and_test_stream_message(fixture_name, self.EXPECTED_SUBJECT, expected_message, **self.api_auth(self.TEST_USER_EMAIL))

    def get_body(self, fixture_name):
        # type: (text_type) -> Union[text_type, Dict[str, text_type]]
        return {}

    def get_payload(self, fixture_name):
        # type: (text_type) -> Union[text_type, Dict[str, text_type]]
        return self.fixture_data(self.FIXTURE_DIR_NAME, fixture_name)

    def build_webhook_url(self):
        # type: () -> text_type
        return ''

    def build_url(self, fixture_name):
        # type: (text_type) -> text_type
        return self.URL_TEMPLATE.format(payload=self.get_payload(fixture_name), stream=self.STREAM_NAME)
