import urllib

from zerver.lib.test_classes import WebhookTestCase


class TravisHookTests(WebhookTestCase):
    STREAM_NAME = "travis"
    URL_TEMPLATE = "/api/v1/external/travis?stream={stream}&api_key={api_key}"
    FIXTURE_DIR_NAME = "travis"
    TOPIC = "builds"

    def test_travis_message(self) -> None:
        """
        Build notifications are generated by Travis after build completes.

        The subject describes the repo and Stash "project". The
        content describes the commits pushed.
        """
        expected_message = (
            "Author: josh_mandel\nBuild status: Passed :thumbs_up:\n"
            "Details: [changes](https://github.com/hl7-fhir/fhir-sv"
            "n/compare/6dccb98bcfd9...6c457d366a31), [build log](ht"
            "tps://travis-ci.org/hl7-fhir/fhir-svn/builds/92495257)"
        )

        self.check_webhook(
            "build",
            self.TOPIC,
            expected_message,
            content_type="application/x-www-form-urlencoded",
        )

    def test_ignore_travis_pull_request_by_default(self) -> None:
        self.subscribe(self.test_user, self.STREAM_NAME)
        result = self.client_post(
            self.url,
            self.get_body("pull_request"),
            content_type="application/x-www-form-urlencoded",
        )
        self.assert_json_success(result)
        msg = self.get_last_message()
        self.assertNotEqual(msg.topic_name(), self.TOPIC)

    def test_travis_pull_requests_are_not_ignored_when_applicable(self) -> None:
        self.url = f"{self.build_webhook_url()}&ignore_pull_requests=false"
        expected_message = (
            "Author: josh_mandel\nBuild status: Passed :thumbs_up:\n"
            "Details: [changes](https://github.com/hl7-fhir/fhir-sv"
            "n/compare/6dccb98bcfd9...6c457d366a31), [build log](ht"
            "tps://travis-ci.org/hl7-fhir/fhir-svn/builds/92495257)"
        )

        self.check_webhook(
            "pull_request",
            self.TOPIC,
            expected_message,
            content_type="application/x-www-form-urlencoded",
        )

    def get_body(self, fixture_name: str) -> str:
        return urllib.parse.urlencode(
            {"payload": self.webhook_fixture_data("travis", fixture_name, file_type="json")}
        )
