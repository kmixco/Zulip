from zerver.lib.test_classes import WebhookTestCase


class SolanoHookTests(WebhookTestCase):
    STREAM_NAME = "solano labs"
    URL_TEMPLATE = "/api/v1/external/solano?api_key={api_key}&stream={stream}"
    FIXTURE_DIR_NAME = "solano"

    def test_solano_message_001(self) -> None:
        """
        Build notifications are generated by Solano Labs after build completes.
        """
        expected_topic = "build update"
        expected_message = """
Build update (see [build log](https://ci.solanolabs.com:443/reports/3316175)):
* **Author**: solano-ci[bot]@users.noreply.github.com
* **Commit**: [5f43840](github.com/fazerlicourice7/solano/commit/5f438401eb7cc7268cbc28438bfa70bb99f48a03)
* **Status**: failed :thumbs_down:
""".strip()

        self.check_webhook(
            "build_001",
            expected_topic,
            expected_message,
            content_type="application/x-www-form-urlencoded",
        )

    def test_solano_message_002(self) -> None:
        """
        Build notifications are generated by Solano Labs after build completes.
        """
        expected_topic = "build update"
        expected_message = """
Build update (see [build log](https://ci.solanolabs.com:443/reports/3316723)):
* **Author**: Unknown
* **Commit**: [5d0b92e](bitbucket.org/fazerlicourice7/test/commits/5d0b92e26448a9e91db794bfed4b8c3556eabc4e)
* **Status**: failed :thumbs_down:
""".strip()

        self.check_webhook(
            "build_002",
            expected_topic,
            expected_message,
            content_type="application/x-www-form-urlencoded",
        )

    def test_solano_message_received(self) -> None:
        """
        Build notifications are generated by Solano Labs after build completes.
        """
        expected_topic = "build update"
        expected_message = """
Build update (see [build log](https://ci.solanolabs.com:443/reports/3317799)):
* **Author**: solano-ci[bot]@users.noreply.github.com
* **Commit**: [191d34f](github.com/anirudhjain75/scipy/commit/191d34f9da8ff7279b051cd68e44223253e18408)
* **Status**: running :arrows_counterclockwise:
""".strip()

        self.check_webhook(
            "received",
            expected_topic,
            expected_message,
            content_type="application/x-www-form-urlencoded",
        )

    def test_solano_test_message(self) -> None:
        expected_topic = "build update"
        expected_message = "Solano webhook set up correctly."

        self.check_webhook(
            "test",
            expected_topic,
            expected_message,
            content_type="application/x-www-form-urlencoded",
        )
