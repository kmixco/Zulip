from zerver.lib.saved_replies import do_create_saved_reply
from zerver.lib.test_classes import ZulipTestCase
from zerver.models import SavedReply, UserProfile


class SavedReplyTests(ZulipTestCase):
    def create_example_saved_reply(self, user: UserProfile) -> int:
        saved_reply = do_create_saved_reply(
            "Welcome message", "**Welcome** to the organization.", user
        )
        return saved_reply.id

    def test_create_saved_reply(self) -> None:
        """Tests creation of saved replies."""

        user = self.example_user("hamlet")
        self.login_user(user)

        result = self.client_get(
            "/json/saved_replies",
        )
        response_dict = self.assert_json_success(result)
        self.assert_length(response_dict["saved_replies"], 0)

        result = self.client_post(
            "/json/saved_replies",
            {"title": "Welcome message", "content": "**Welcome** to the organization."},
        )
        response_dict = self.assert_json_success(result)
        saved_reply_id = response_dict["saved_reply_id"]

        result = self.client_get(
            "/json/saved_replies",
        )
        response_dict = self.assert_json_success(result)
        self.assert_length(response_dict["saved_replies"], 1)
        self.assertEqual(saved_reply_id, response_dict["saved_replies"][0]["id"])

        # Tests if the title is truncated when the length exceeds `MAX_TITLE_LENGTH`.
        title = "This is very very long saved reply title."
        result = self.client_post(
            "/json/saved_replies",
            {"title": title, "content": "Hello"},
        )
        response_dict = self.assert_json_success(result)
        saved_title = SavedReply.objects.get(id=response_dict["saved_reply_id"]).title
        self.assertEqual(saved_title, title[: SavedReply.MAX_TITLE_LENGTH])

        # Tests if error is thrown when title is an empty string.
        result = self.client_post(
            "/json/saved_replies",
            {"title": "", "content": "Hello"},
        )
        self.assert_json_error(result, "Title cannot be empty.", status_code=400)

        # Tests if error is thrown when content is an empty string.
        result = self.client_post(
            "/json/saved_replies",
            {"title": "Test saved reply.", "content": ""},
        )
        self.assert_json_error(result, "Content cannot be empty.", status_code=400)

    def test_delete_saved_reply(self) -> None:
        """Tests deletion of saved replies."""

        user = self.example_user("hamlet")
        self.login_user(user)
        saved_reply_id = self.create_example_saved_reply(user)

        result = self.client_get(
            "/json/saved_replies",
        )
        response_dict = self.assert_json_success(result)
        self.assert_length(response_dict["saved_replies"], 1)

        result = self.client_delete(
            f"/json/saved_replies/{saved_reply_id}",
        )
        self.assert_json_success(result)

        result = self.client_get(
            "/json/saved_replies",
        )
        response_dict = self.assert_json_success(result)
        self.assert_length(response_dict["saved_replies"], 0)

        # Tests if error is thrown when the provided ID does not exist.
        result = self.client_delete(
            "/json/saved_replies/10",
        )
        self.assert_json_error(result, "Saved reply does not exist.", status_code=404)
