# -*- coding: utf-8 -*-
from mock import MagicMock, patch

from zerver.lib.test_classes import WebhookTestCase
from zerver.lib.webhooks.git import COMMITS_LIMIT


class GitlabHookTests(WebhookTestCase):
    STREAM_NAME = 'gitlab'
    URL_TEMPLATE = "/api/v1/external/gitlab?&api_key={api_key}&stream={stream}"
    FIXTURE_DIR_NAME = 'gitlab'

    def test_push_event_specified_topic(self) -> None:
        self.url = self.build_webhook_url("topic=Specific%20topic")
        expected_topic = u"Specific topic"
        expected_message = u"Tomasz Kolek [pushed](https://gitlab.com/tomaszkolek0/my-awesome-project/compare/5fcdd5551fc3085df79bece2c32b1400802ac407...eb6ae1e591e0819dc5bf187c6bfe18ec065a80e9) 2 commits to branch tomek.\n\n* b ([66abd2d](https://gitlab.com/tomaszkolek0/my-awesome-project/commit/66abd2da28809ffa128ed0447965cf11d7f863a7))\n* c ([eb6ae1e](https://gitlab.com/tomaszkolek0/my-awesome-project/commit/eb6ae1e591e0819dc5bf187c6bfe18ec065a80e9))"
        self.send_and_test_stream_message('push_hook', expected_topic, expected_message)

    def test_push_event_message(self) -> None:
        expected_topic = u"my-awesome-project / tomek"
        expected_message = u"Tomasz Kolek [pushed](https://gitlab.com/tomaszkolek0/my-awesome-project/compare/5fcdd5551fc3085df79bece2c32b1400802ac407...eb6ae1e591e0819dc5bf187c6bfe18ec065a80e9) 2 commits to branch tomek.\n\n* b ([66abd2d](https://gitlab.com/tomaszkolek0/my-awesome-project/commit/66abd2da28809ffa128ed0447965cf11d7f863a7))\n* c ([eb6ae1e](https://gitlab.com/tomaszkolek0/my-awesome-project/commit/eb6ae1e591e0819dc5bf187c6bfe18ec065a80e9))"
        self.send_and_test_stream_message('push_hook', expected_topic, expected_message)

    def test_push_local_branch_without_commits(self) -> None:
        expected_topic = u"my-awesome-project / changes"
        expected_message = u"Eeshan Garg [pushed](https://gitlab.com/eeshangarg/my-awesome-project/compare/0000000000000000000000000000000000000000...68d7a5528cf423dfaac37dd62a56ac9cc8a884e3) the branch changes."
        self.send_and_test_stream_message('push_hook__push_local_branch_without_commits', expected_topic, expected_message)

    def test_push_event_message_filtered_by_branches(self) -> None:
        self.url = self.build_webhook_url(branches='master,tomek')
        expected_topic = u"my-awesome-project / tomek"
        expected_message = u"Tomasz Kolek [pushed](https://gitlab.com/tomaszkolek0/my-awesome-project/compare/5fcdd5551fc3085df79bece2c32b1400802ac407...eb6ae1e591e0819dc5bf187c6bfe18ec065a80e9) 2 commits to branch tomek.\n\n* b ([66abd2d](https://gitlab.com/tomaszkolek0/my-awesome-project/commit/66abd2da28809ffa128ed0447965cf11d7f863a7))\n* c ([eb6ae1e](https://gitlab.com/tomaszkolek0/my-awesome-project/commit/eb6ae1e591e0819dc5bf187c6bfe18ec065a80e9))"
        self.send_and_test_stream_message('push_hook', expected_topic, expected_message)

    def test_push_multiple_committers(self) -> None:
        expected_topic = u"my-awesome-project / tomek"
        expected_message = u"Tomasz Kolek [pushed](https://gitlab.com/tomaszkolek0/my-awesome-project/compare/5fcdd5551fc3085df79bece2c32b1400802ac407...eb6ae1e591e0819dc5bf187c6bfe18ec065a80e9) 2 commits to branch tomek. Commits by Ben (1) and Tomasz Kolek (1).\n\n* b ([66abd2d](https://gitlab.com/tomaszkolek0/my-awesome-project/commit/66abd2da28809ffa128ed0447965cf11d7f863a7))\n* c ([eb6ae1e](https://gitlab.com/tomaszkolek0/my-awesome-project/commit/eb6ae1e591e0819dc5bf187c6bfe18ec065a80e9))"
        self.send_and_test_stream_message('push_hook__push_multiple_committers', expected_topic, expected_message)

    def test_push_multiple_committers_with_others(self) -> None:
        expected_topic = u"my-awesome-project / tomek"
        commit_info = u"* b ([eb6ae1e](https://gitlab.com/tomaszkolek0/my-awesome-project/commit/eb6ae1e591e0819dc5bf187c6bfe18ec065a80e9))\n"
        expected_message = u"Tomasz Kolek [pushed](https://gitlab.com/tomaszkolek0/my-awesome-project/compare/5fcdd5551fc3085df79bece2c32b1400802ac407...eb6ae1e591e0819dc5bf187c6bfe18ec065a80e9) 7 commits to branch tomek. Commits by Ben (3), baxterthehacker (2), James (1) and others (1).\n\n{}* b ([eb6ae1e](https://gitlab.com/tomaszkolek0/my-awesome-project/commit/eb6ae1e591e0819dc5bf187c6bfe18ec065a80e9))".format(commit_info * 6)
        self.send_and_test_stream_message('push_hook__push_multiple_committers_with_others', expected_topic, expected_message)

    def test_push_commits_more_than_limit_event_message(self) -> None:
        expected_topic = u"my-awesome-project / tomek"
        commits_info = u'* b ([66abd2d](https://gitlab.com/tomaszkolek0/my-awesome-project/commit/66abd2da28809ffa128ed0447965cf11d7f863a7))\n'
        expected_message = u"Tomasz Kolek [pushed](https://gitlab.com/tomaszkolek0/my-awesome-project/compare/5fcdd5551fc3085df79bece2c32b1400802ac407...eb6ae1e591e0819dc5bf187c6bfe18ec065a80e9) 50 commits to branch tomek.\n\n{}[and {} more commit(s)]".format(
            commits_info * COMMITS_LIMIT,
            50 - COMMITS_LIMIT,
        )
        self.send_and_test_stream_message('push_hook__push_commits_more_than_limit', expected_topic, expected_message)

    def test_push_commits_more_than_limit_message_filtered_by_branches(self) -> None:
        self.url = self.build_webhook_url(branches='master,tomek')
        expected_topic = u"my-awesome-project / tomek"
        commits_info = u'* b ([66abd2d](https://gitlab.com/tomaszkolek0/my-awesome-project/commit/66abd2da28809ffa128ed0447965cf11d7f863a7))\n'
        expected_message = u"Tomasz Kolek [pushed](https://gitlab.com/tomaszkolek0/my-awesome-project/compare/5fcdd5551fc3085df79bece2c32b1400802ac407...eb6ae1e591e0819dc5bf187c6bfe18ec065a80e9) 50 commits to branch tomek.\n\n{}[and {} more commit(s)]".format(
            commits_info * COMMITS_LIMIT,
            50 - COMMITS_LIMIT,
        )
        self.send_and_test_stream_message('push_hook__push_commits_more_than_limit', expected_topic, expected_message)

    def test_remove_branch_event_message(self) -> None:
        expected_topic = u"my-awesome-project / tomek"
        expected_message = u"Tomasz Kolek deleted branch tomek."

        self.send_and_test_stream_message('push_hook__remove_branch', expected_topic, expected_message)

    def test_add_tag_event_message(self) -> None:
        expected_topic = u"my-awesome-project"
        expected_message = u"Tomasz Kolek pushed tag xyz."

        self.send_and_test_stream_message(
            'tag_push_hook__add_tag',
            expected_topic,
            expected_message,
            HTTP_X_GITLAB_EVENT="Tag Push Hook",
        )

    def test_remove_tag_event_message(self) -> None:
        expected_topic = u"my-awesome-project"
        expected_message = u"Tomasz Kolek removed tag xyz."

        self.send_and_test_stream_message(
            'tag_push_hook__remove_tag',
            expected_topic,
            expected_message)

    def test_create_issue_without_assignee_event_message(self) -> None:
        expected_topic = u"my-awesome-project / Issue #1 Issue title"
        expected_message = u"Tomasz Kolek created [Issue #1](https://gitlab.com/tomaszkolek0/my-awesome-project/issues/1):\n\n~~~ quote\nIssue description\n~~~"

        self.send_and_test_stream_message(
            'issue_hook__issue_created_without_assignee',
            expected_topic,
            expected_message)

    def test_create_confidential_issue_without_assignee_event_message(self) -> None:
        expected_subject = u"testing / Issue #1 Testing"
        expected_message = u"Joe Bloggs created [Issue #1](https://gitlab.example.co.uk/joe.bloggs/testing/issues/1):\n\n~~~ quote\nTesting\n~~~"

        self.send_and_test_stream_message(
            'issue_hook__confidential_issue_created_without_assignee',
            expected_subject,
            expected_message)

    def test_create_issue_with_custom_topic_in_url(self) -> None:
        self.url = self.build_webhook_url(topic='notifications')
        expected_topic = u"notifications"
        expected_message = u"Tomasz Kolek created [Issue #1 Issue title](https://gitlab.com/tomaszkolek0/my-awesome-project/issues/1):\n\n~~~ quote\nIssue description\n~~~"

        self.send_and_test_stream_message(
            'issue_hook__issue_created_without_assignee',
            expected_topic,
            expected_message)

    def test_create_issue_with_assignee_event_message(self) -> None:
        expected_topic = u"my-awesome-project / Issue #1 Issue title"
        expected_message = u"Tomasz Kolek created [Issue #1](https://gitlab.com/tomaszkolek0/my-awesome-project/issues/1) (assigned to Tomasz Kolek):\n\n~~~ quote\nIssue description\n~~~"

        self.send_and_test_stream_message(
            'issue_hook__issue_created_with_assignee',
            expected_topic,
            expected_message)

    def test_create_issue_with_two_assignees_event_message(self) -> None:
        expected_subject = u"Zulip GitLab Test / Issue #2 Zulip Test Issue 2"
        expected_message = u"Adam Birds created [Issue #2](https://gitlab.com/adambirds/zulip-gitlab-test/issues/2) (assigned to adambirds and eeshangarg):\n\n~~~ quote\nZulip Test Issue 2\n~~~"

        self.send_and_test_stream_message(
            'issue_hook__issue_created_with_two_assignees',
            expected_subject,
            expected_message)

    def test_create_issue_with_three_assignees_event_message(self) -> None:
        expected_subject = u"Zulip GitLab Test / Issue #2 Zulip Test Issue 2"
        expected_message = u"Adam Birds created [Issue #2](https://gitlab.com/adambirds/zulip-gitlab-test/issues/2) (assigned to adambirds, eeshangarg and timabbott):\n\n~~~ quote\nZulip Test Issue 2\n~~~"

        self.send_and_test_stream_message(
            'issue_hook__issue_created_with_three_assignees',
            expected_subject,
            expected_message)

    def test_create_confidential_issue_with_assignee_event_message(self) -> None:
        expected_subject = u"testing / Issue #2 Testing"
        expected_message = u"Joe Bloggs created [Issue #2](https://gitlab.example.co.uk/joe.bloggs/testing/issues/2) (assigned to joe.bloggs):\n\n~~~ quote\nTesting\n~~~"

        self.send_and_test_stream_message(
            'issue_hook__confidential_issue_created_with_assignee',
            expected_subject,
            expected_message)

    def test_create_issue_with_hidden_comment_in_description(self) -> None:
        expected_topic = u"public-repo / Issue #3 New Issue with hidden comment"
        expected_message = u"Eeshan Garg created [Issue #3](https://gitlab.com/eeshangarg/public-repo/issues/3):\n\n~~~ quote\nThis description actually has a hidden comment in it!\n~~~"

        self.send_and_test_stream_message(
            'issue_hook__issue_created_with_hidden_comment_in_description',
            expected_topic,
            expected_message)

    def test_create_confidential_issue_with_hidden_comment_in_description(self) -> None:
        expected_subject = u"testing / Issue #1 Testing"
        expected_message = u"Joe Bloggs created [Issue #1](https://gitlab.example.co.uk/joe.bloggs/testing/issues/1):\n\n~~~ quote\nThis description actually has a hidden comment in it!\n~~~"

        self.send_and_test_stream_message(
            'issue_hook__confidential_issue_created_with_hidden_comment_in_description',
            expected_subject,
            expected_message)

    def test_create_issue_with_null_description(self) -> None:
        expected_topic = u"my-awesome-project / Issue #7 Issue without description"
        expected_message = u"Eeshan Garg created [Issue #7](https://gitlab.com/eeshangarg/my-awesome-project/issues/7)."
        self.send_and_test_stream_message(
            'issue_hook__issue_opened_with_null_description',
            expected_topic,
            expected_message)

    def test_update_issue_event_message(self) -> None:
        expected_topic = u"my-awesome-project / Issue #1 Issue title_new"
        expected_message = u"Tomasz Kolek updated [Issue #1](https://gitlab.com/tomaszkolek0/my-awesome-project/issues/1)."

        self.send_and_test_stream_message(
            'issue_hook__issue_updated',
            expected_topic,
            expected_message)

    def test_update_confidential_issue_event_message(self) -> None:
        expected_subject = u"testing / Issue #1 Testing"
        expected_message = u"Joe Bloggs updated [Issue #1](https://gitlab.example.co.uk/joe.bloggs/testing/issues/1)."

        self.send_and_test_stream_message(
            'issue_hook__confidential_issue_updated',
            expected_subject,
            expected_message)

    def test_update_issue_with_custom_topic_in_url(self) -> None:
        self.url = self.build_webhook_url(topic='notifications')
        expected_topic = u"notifications"
        expected_message = u"Tomasz Kolek updated [Issue #1 Issue title_new](https://gitlab.com/tomaszkolek0/my-awesome-project/issues/1)."

        self.send_and_test_stream_message(
            'issue_hook__issue_updated',
            expected_topic,
            expected_message)

    def test_close_issue_event_message(self) -> None:
        expected_topic = u"my-awesome-project / Issue #1 Issue title_new"
        expected_message = u"Tomasz Kolek closed [Issue #1](https://gitlab.com/tomaszkolek0/my-awesome-project/issues/1)."

        self.send_and_test_stream_message(
            'issue_hook__issue_closed',
            expected_topic,
            expected_message)

    def test_close_confidential_issue_event_message(self) -> None:
        expected_subject = u"testing / Issue #1 Testing Test"
        expected_message = u"Joe Bloggs closed [Issue #1](https://gitlab.example.co.uk/joe.bloggs/testing/issues/1)."

        self.send_and_test_stream_message(
            'issue_hook__confidential_issue_closed',
            expected_subject,
            expected_message)

    def test_reopen_issue_event_message(self) -> None:
        expected_topic = u"my-awesome-project / Issue #1 Issue title_new"
        expected_message = u"Tomasz Kolek reopened [Issue #1](https://gitlab.com/tomaszkolek0/my-awesome-project/issues/1)."

        self.send_and_test_stream_message(
            'issue_hook__issue_reopened',
            expected_topic,
            expected_message)

    def test_reopen_confidential_issue_event_message(self) -> None:
        expected_subject = u"testing / Issue #1 Testing Test"
        expected_message = u"Joe Bloggs reopened [Issue #1](https://gitlab.example.co.uk/joe.bloggs/testing/issues/1)."

        self.send_and_test_stream_message(
            'issue_hook__confidential_issue_reopened',
            expected_subject,
            expected_message)

    def test_note_commit_event_message(self) -> None:
        expected_topic = u"my-awesome-project"
        expected_message = u"Tomasz Kolek [commented](https://gitlab.com/tomaszkolek0/my-awesome-project/commit/66abd2da28809ffa128ed0447965cf11d7f863a7#note_14169211) on [66abd2d](https://gitlab.com/tomaszkolek0/my-awesome-project/commit/66abd2da28809ffa128ed0447965cf11d7f863a7):\n~~~ quote\nnice commit\n~~~"

        self.send_and_test_stream_message(
            'note_hook__commit_note',
            expected_topic,
            expected_message)

    def test_note_merge_request_event_message(self) -> None:
        expected_topic = u"my-awesome-project / MR #1 Tomek"
        expected_message = u"Tomasz Kolek [commented](https://gitlab.com/tomaszkolek0/my-awesome-project/merge_requests/1#note_14171860) on [MR #1](https://gitlab.com/tomaszkolek0/my-awesome-project/merge_requests/1):\n\n~~~ quote\nNice merge request!\n~~~"

        self.send_and_test_stream_message(
            'note_hook__merge_request_note',
            expected_topic,
            expected_message)

    def test_note_merge_request_with_custom_topic_in_url(self) -> None:
        self.url = self.build_webhook_url(topic='notifications')
        expected_topic = u"notifications"
        expected_message = u"Tomasz Kolek [commented](https://gitlab.com/tomaszkolek0/my-awesome-project/merge_requests/1#note_14171860) on [MR #1 Tomek](https://gitlab.com/tomaszkolek0/my-awesome-project/merge_requests/1):\n\n~~~ quote\nNice merge request!\n~~~"

        self.send_and_test_stream_message(
            'note_hook__merge_request_note',
            expected_topic,
            expected_message)

    def test_note_issue_event_message(self) -> None:
        expected_topic = u"my-awesome-project / Issue #2 abc"
        expected_message = u"Tomasz Kolek [commented](https://gitlab.com/tomaszkolek0/my-awesome-project/issues/2#note_14172057) on [Issue #2](https://gitlab.com/tomaszkolek0/my-awesome-project/issues/2):\n\n~~~ quote\nNice issue\n~~~"

        self.send_and_test_stream_message(
            'note_hook__issue_note',
            expected_topic,
            expected_message)

    def test_note_confidential_issue_event_message(self) -> None:
        expected_subject = u"Test / Issue #3 Test"
        expected_message = u"Joe Bloggs [commented](https://gitlab.com/joebloggs/test/issues/3#note_101638770) on [Issue #3](https://gitlab.com/joebloggs/test/issues/3):\n\n~~~ quote\nTest\n~~~"

        self.send_and_test_stream_message(
            'note_hook__confidential_issue_note',
            expected_subject,
            expected_message)

    def test_note_issue_with_custom_topic_in_url(self) -> None:
        self.url = self.build_webhook_url(topic='notifications')
        expected_topic = u"notifications"
        expected_message = u"Tomasz Kolek [commented](https://gitlab.com/tomaszkolek0/my-awesome-project/issues/2#note_14172057) on [Issue #2 abc](https://gitlab.com/tomaszkolek0/my-awesome-project/issues/2):\n\n~~~ quote\nNice issue\n~~~"

        self.send_and_test_stream_message(
            'note_hook__issue_note',
            expected_topic,
            expected_message)

    def test_note_snippet_event_message(self) -> None:
        expected_topic = u"my-awesome-project / Snippet #2 test"
        expected_message = u"Tomasz Kolek [commented](https://gitlab.com/tomaszkolek0/my-awesome-project/snippets/2#note_14172058) on [Snippet #2](https://gitlab.com/tomaszkolek0/my-awesome-project/snippets/2):\n\n~~~ quote\nNice snippet\n~~~"

        self.send_and_test_stream_message(
            'note_hook__snippet_note',
            expected_topic,
            expected_message)

    def test_note_snippet_with_custom_topic_in_url(self) -> None:
        self.url = self.build_webhook_url(topic='notifications')
        expected_topic = u"notifications"
        expected_message = u"Tomasz Kolek [commented](https://gitlab.com/tomaszkolek0/my-awesome-project/snippets/2#note_14172058) on [Snippet #2 test](https://gitlab.com/tomaszkolek0/my-awesome-project/snippets/2):\n\n~~~ quote\nNice snippet\n~~~"

        self.send_and_test_stream_message(
            'note_hook__snippet_note',
            expected_topic,
            expected_message)

    def test_merge_request_created_without_assignee_event_message(self) -> None:
        expected_topic = u"my-awesome-project / MR #2 NEW MR"
        expected_message = u"Tomasz Kolek created [MR #2](https://gitlab.com/tomaszkolek0/my-awesome-project/merge_requests/2) from `tomek` to `master`:\n\n~~~ quote\ndescription of merge request\n~~~"

        self.send_and_test_stream_message(
            'merge_request_hook__merge_request_created_without_assignee',
            expected_topic,
            expected_message)

    def test_merge_request_created_with_custom_topic_in_url(self) -> None:
        self.url = self.build_webhook_url(topic='notifications')
        expected_topic = u"notifications"
        expected_message = u"Tomasz Kolek created [MR #2 NEW MR](https://gitlab.com/tomaszkolek0/my-awesome-project/merge_requests/2) from `tomek` to `master`:\n\n~~~ quote\ndescription of merge request\n~~~"

        self.send_and_test_stream_message(
            'merge_request_hook__merge_request_created_without_assignee',
            expected_topic,
            expected_message)

    def test_merge_request_created_with_assignee_event_message(self) -> None:
        expected_topic = u"my-awesome-project / MR #3 New Merge Request"
        expected_message = u"Tomasz Kolek created [MR #3](https://gitlab.com/tomaszkolek0/my-awesome-project/merge_requests/3) (assigned to Tomasz Kolek) from `tomek` to `master`:\n\n~~~ quote\ndescription of merge request\n~~~"
        self.send_and_test_stream_message(
            'merge_request_hook__merge_request_created_with_assignee',
            expected_topic,
            expected_message)

    def test_merge_request_closed_event_message(self) -> None:
        expected_topic = u"my-awesome-project / MR #2 NEW MR"
        expected_message = u"Tomasz Kolek closed [MR #2](https://gitlab.com/tomaszkolek0/my-awesome-project/merge_requests/2)."

        self.send_and_test_stream_message(
            'merge_request_hook__merge_request_closed',
            expected_topic,
            expected_message)

    def test_merge_request_closed_with_custom_topic_in_url(self) -> None:
        self.url = self.build_webhook_url(topic='notifications')
        expected_topic = u"notifications"
        expected_message = u"Tomasz Kolek closed [MR #2 NEW MR](https://gitlab.com/tomaszkolek0/my-awesome-project/merge_requests/2)."

        self.send_and_test_stream_message(
            'merge_request_hook__merge_request_closed',
            expected_topic,
            expected_message)

    def test_merge_request_reopened_event_message(self) -> None:
        expected_topic = u"my-awesome-project / MR #1 Update the README with author ..."
        expected_message = u"Eeshan Garg reopened [MR #1](https://gitlab.com/eeshangarg/my-awesome-project/merge_requests/1)."

        self.send_and_test_stream_message(
            'merge_request_hook__merge_request_reopened',
            expected_topic,
            expected_message)

    def test_merge_request_approved_event_message(self) -> None:
        expected_topic = u"my-awesome-project / MR #1 Update the README with author ..."
        expected_message = u"Eeshan Garg approved [MR #1](https://gitlab.com/eeshangarg/my-awesome-project/merge_requests/1)."

        self.send_and_test_stream_message(
            'merge_request_hook__merge_request_approved',
            expected_topic,
            expected_message)

    def test_merge_request_updated_event_message(self) -> None:
        expected_topic = u"my-awesome-project / MR #3 New Merge Request"
        expected_message = u"Tomasz Kolek updated [MR #3](https://gitlab.com/tomaszkolek0/my-awesome-project/merge_requests/3) (assigned to Tomasz Kolek) from `tomek` to `master`:\n\n~~~ quote\nupdated desc\n~~~"
        self.send_and_test_stream_message(
            'merge_request_hook__merge_request_updated',
            expected_topic,
            expected_message)

    def test_merge_request_added_commit_event_message(self) -> None:
        expected_topic = u"my-awesome-project / MR #3 New Merge Request"
        expected_message = u"Tomasz Kolek added commit(s) to [MR #3](https://gitlab.com/tomaszkolek0/my-awesome-project/merge_requests/3)."
        self.send_and_test_stream_message(
            'merge_request_hook__merge_request_added_commit',
            expected_topic,
            expected_message)

    def test_merge_request_merged_event_message(self) -> None:
        expected_topic = u"my-awesome-project / MR #3 New Merge Request"
        expected_message = u"Tomasz Kolek merged [MR #3](https://gitlab.com/tomaszkolek0/my-awesome-project/merge_requests/3)."

        self.send_and_test_stream_message(
            'merge_request_hook__merge_request_merged',
            expected_topic,
            expected_message)

    def test_wiki_page_opened_event_message(self) -> None:
        expected_topic = u"my-awesome-project"
        expected_message = u"Tomasz Kolek created [Wiki Page \"how to\"](https://gitlab.com/tomaszkolek0/my-awesome-project/wikis/how-to)."

        self.send_and_test_stream_message(
            'wiki_page_hook__wiki_page_opened',
            expected_topic,
            expected_message)

    def test_wiki_page_edited_event_message(self) -> None:
        expected_topic = u"my-awesome-project"
        expected_message = u"Tomasz Kolek updated [Wiki Page \"how to\"](https://gitlab.com/tomaszkolek0/my-awesome-project/wikis/how-to)."

        self.send_and_test_stream_message(
            'wiki_page_hook__wiki_page_edited',
            expected_topic,
            expected_message)

    def test_build_created_event_message(self) -> None:
        expected_topic = u"my-awesome-project / master"
        expected_message = u"Build job_name from test stage was created."

        self.send_and_test_stream_message(
            'build_created',
            expected_topic,
            expected_message,
            HTTP_X_GITLAB_EVENT="Job Hook"
        )

    def test_build_started_event_message(self) -> None:
        expected_topic = u"my-awesome-project / master"
        expected_message = u"Build job_name from test stage started."

        self.send_and_test_stream_message(
            'build_started',
            expected_topic,
            expected_message,
            HTTP_X_GITLAB_EVENT="Job Hook"
        )

    def test_build_succeeded_event_message(self) -> None:
        expected_topic = u"my-awesome-project / master"
        expected_message = u"Build job_name from test stage changed status to success."

        self.send_and_test_stream_message(
            'build_succeeded',
            expected_topic,
            expected_message,
            HTTP_X_GITLAB_EVENT="Job Hook"
        )

    def test_build_created_event_message_legacy_event_name(self) -> None:
        expected_topic = u"my-awesome-project / master"
        expected_message = u"Build job_name from test stage was created."

        self.send_and_test_stream_message(
            'build_created',
            expected_topic,
            expected_message,
            HTTP_X_GITLAB_EVENT="Build Hook"
        )

    def test_build_started_event_message_legacy_event_name(self) -> None:
        expected_topic = u"my-awesome-project / master"
        expected_message = u"Build job_name from test stage started."

        self.send_and_test_stream_message(
            'build_started',
            expected_topic,
            expected_message,
            HTTP_X_GITLAB_EVENT="Build Hook"
        )

    def test_build_succeeded_event_message_legacy_event_name(self) -> None:
        expected_topic = u"my-awesome-project / master"
        expected_message = u"Build job_name from test stage changed status to success."

        self.send_and_test_stream_message(
            'build_succeeded',
            expected_topic,
            expected_message,
            HTTP_X_GITLAB_EVENT="Build Hook"
        )

    def test_pipeline_succeeded_event_message(self) -> None:
        expected_topic = u"my-awesome-project / master"
        expected_message = u"Pipeline changed status to success with build(s):\n* job_name2 - success\n* job_name - success."

        self.send_and_test_stream_message(
            'pipeline_hook__pipeline_succeeded',
            expected_topic,
            expected_message
        )

    def test_pipeline_started_event_message(self) -> None:
        expected_topic = u"my-awesome-project / master"
        expected_message = u"Pipeline started with build(s):\n* job_name - running\n* job_name2 - pending."

        self.send_and_test_stream_message(
            'pipeline_hook__pipeline_started',
            expected_topic,
            expected_message
        )

    def test_pipeline_pending_event_message(self) -> None:
        expected_topic = u"my-awesome-project / master"
        expected_message = u"Pipeline was created with build(s):\n* job_name2 - pending\n* job_name - created."

        self.send_and_test_stream_message(
            'pipeline_hook__pipeline_pending',
            expected_topic,
            expected_message
        )

    def test_issue_type_test_payload(self) -> None:
        expected_topic = u'public-repo'
        expected_message = u"Webhook for **public-repo** has been configured successfully! :tada:"

        self.send_and_test_stream_message(
            'test_hook__issue_test_payload',
            expected_topic,
            expected_message
        )

    @patch('zerver.lib.webhooks.common.check_send_webhook_message')
    def test_push_event_message_filtered_by_branches_ignore(
            self, check_send_webhook_message_mock: MagicMock) -> None:
        self.url = self.build_webhook_url(branches='master,development')
        payload = self.get_body('push_hook')
        result = self.client_post(self.url, payload, HTTP_X_GITLAB_EVENT='Push Hook', content_type="application/json")
        self.assertFalse(check_send_webhook_message_mock.called)
        self.assert_json_success(result)

    @patch('zerver.lib.webhooks.common.check_send_webhook_message')
    def test_push_commits_more_than_limit_message_filtered_by_branches_ignore(
            self, check_send_webhook_message_mock: MagicMock) -> None:
        self.url = self.build_webhook_url(branches='master,development')
        payload = self.get_body('push_hook__push_commits_more_than_limit')
        result = self.client_post(self.url, payload, HTTP_X_GITLAB_EVENT='Push Hook', content_type="application/json")
        self.assertFalse(check_send_webhook_message_mock.called)
        self.assert_json_success(result)
