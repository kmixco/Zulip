import os

from django.conf import settings

from zerver.lib.test_classes import ZulipTestCase
from zerver.lib.test_helpers import (
    create_s3_buckets,
    use_s3_backend,
)
from zerver.lib.upload.s3 import upload_image_to_s3


class TusdTest(ZulipTestCase):
    def test_tusd_auth(self) -> None:
        body = {
            "Upload": {
                "ID": "",
            },
        }
        result = self.client_post(
            f"/tusd/hooks?secret={settings.SHARED_SECRET}",
            body,
            content_type="application/json",
            HTTP_HOOK_NAME="pre-create",
        )
        self.assert_json_error_contains(
            result, "Not logged in: API authentication or user session required", 401
        )

    def test_tusd_pre_create_hook(self) -> None:
        self.login("hamlet")
        body = {
            "Upload": {
                "ID": "",
                "IsFinal": False,
                "IsPartial": False,
                "MetaData": {
                    "filename": "zulip.txt",
                    "filetype": "text",
                    "name": "zulip.txt",
                    "type": "text",
                },
                "Offset": 0,
                "PartialUploads": None,
                "Size": settings.MAX_FILE_UPLOAD_SIZE * 1024 * 1024 - 100,
                "SizeIsDeferred": False,
                "Storage": None,
            },
        }
        result = self.client_post(
            f"/tusd/hooks?secret={settings.SHARED_SECRET}",
            body,
            content_type="application/json",
            HTTP_HOOK_NAME="pre-create",
        )
        self.assert_json_success(result)

    def test_file_too_big_failure(self) -> None:
        self.login("hamlet")
        body = {
            "Upload": {
                "ID": "",
                "IsFinal": False,
                "Offset": 0,
                "Size": settings.MAX_FILE_UPLOAD_SIZE * 1024 * 1024 + 100,
                "SizeIsDeferred": False,
                "Storage": None,
            },
        }
        result = self.client_post(
            f"/tusd/hooks?secret={settings.SHARED_SECRET}",
            body,
            content_type="application/json",
            HTTP_HOOK_NAME="pre-create",
        )

        self.assert_json_error(
            result,
            f"Uploaded file is larger than the allowed limit of {settings.MAX_FILE_UPLOAD_SIZE} MiB",
        )

    def test_differed_size(self) -> None:
        self.login("hamlet")
        body = {
            "Upload": {
                "ID": "",
                "IsFinal": False,
                "IsPartial": False,
                "MetaData": {
                    "filename": "zulip.txt",
                    "filetype": "text",
                    "name": "zulip.txt",
                    "type": "text",
                },
                "Offset": 0,
                "PartialUploads": None,
                "Size": settings.MAX_FILE_UPLOAD_SIZE * 1024 * 1024 - 100,
                "SizeIsDeferred": True,
                "Storage": None,
            },
        }
        result = self.client_post(
            f"/tusd/hooks?secret={settings.SHARED_SECRET}",
            body,
            content_type="application/json",
            HTTP_HOOK_NAME="pre-create",
        )
        self.assert_json_error(result, msg="Deferred file size not allowed.")

    def test_tusd_pre_finish_hook(self) -> None:
        self.login("hamlet")

        assert settings.MAX_FILE_UPLOAD_SIZE is not None
        assert settings.LOCAL_FILES_DIR is not None
        assert settings.LOCAL_UPLOADS_DIR is not None

        file_id = "e4b4acc5ddb8675d3af4e75a1a095bd7"
        file_path = os.path.join(settings.LOCAL_UPLOADS_DIR, "tusd", file_id)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, "+bw") as f:
            f.write(os.urandom(100))
            f.close()
        self.assertTrue(os.path.exists(file_path))

        body = {
            "Upload": {
                "ID": file_id,
                "IsFinal": False,
                "IsPartial": False,
                "MetaData": {
                    "filename": "zulip.txt",
                    "filetype": "application/zip",
                    "name": "zulip.txt",
                    "type": "application/zip",
                },
                "Offset": 0,
                "PartialUploads": None,
                "Size": 100,
                "SizeIsDeferred": False,
                "Storage": {"Type": "filestore", "Path": file_path},
            },
        }
        result = self.client_post(
            f"/tusd/hooks?secret={settings.SHARED_SECRET}",
            body,
            content_type="application/json",
            HTTP_HOOK_NAME="pre-finish",
        )
        self.assert_json_success(result)

        result = self.client_get(f"/json/user_uploads/{file_id}")
        result_data = self.assert_json_success(result)

        upload_base = "/user_uploads/"
        path = result_data["url"][len(upload_base) :]

        self.assertTrue(os.path.exists(os.path.join(settings.LOCAL_FILES_DIR, path)))

    def test_tusd_invalid_hook(self) -> None:
        self.login("hamlet")
        body = {"Upload": {"ID": "xyz"}}
        result = self.client_post(
            f"/tusd/hooks?secret={settings.SHARED_SECRET}",
            body,
            content_type="application/json",
            HTTP_HOOK_NAME="pre-xyz",
        )
        self.assert_json_error(result, "Unexpected hook.")

    @use_s3_backend
    def test_tusd_s3_upload(self) -> None:
        user = self.example_user("hamlet")
        self.login_user(user)
        bucket = create_s3_buckets(settings.S3_AUTH_UPLOADS_BUCKET)[0]
        assert settings.MAX_FILE_UPLOAD_SIZE is not None
        file_id = "e4b4acc5ddb8675d3af4e75a1a095bd7"
        path_id = f"tusd/{file_id}"
        body = {
            "Upload": {
                "ID": f"{file_id}+xyz",
                "IsFinal": False,
                "IsPartial": False,
                "MetaData": {
                    "filename": "brijsiyag.zip",
                    "filetype": "application/zip",
                    "name": "brijsiyag.zip",
                    "type": "application/zip",
                },
                "Offset": 0,
                "PartialUploads": None,
                "Size": settings.MAX_FILE_UPLOAD_SIZE * 1024 * 1024 - 100,
                "SizeIsDeferred": False,
                "Storage": {"Type": "s3store", "Key": path_id},
            },
        }

        upload_image_to_s3(bucket, f"tusd/{file_id}", None, user, b"zulip!")

        result = self.client_post(
            f"/tusd/hooks?secret={settings.SHARED_SECRET}",
            body,
            content_type="application/json",
            HTTP_HOOK_NAME="pre-finish",
        )
        self.assert_json_success(result)

        result = self.client_get(f"/json/user_uploads/{file_id}")
        result_data = self.assert_json_success(result)

        upload_base = "/user_uploads/"
        url = result_data["url"]
        path_id = url[len(upload_base) :]

        content = bucket.Object(path_id).get()["Body"].read()
        self.assertEqual(b"zulip!", content)

    def test_local_file_move_fails(self) -> None:
        self.login("hamlet")
        file_id = "e4b4acc5ddb8675d3af4e75a1a095bd7"
        assert settings.LOCAL_UPLOADS_DIR is not None
        file_path = os.path.join(settings.LOCAL_UPLOADS_DIR, "tusd", file_id)
        body = {
            "Upload": {
                "ID": file_id,
                "IsFinal": False,
                "IsPartial": False,
                "MetaData": {
                    "filename": "zulip.txt",
                    "filetype": "application/zip",
                    "name": "zulip.txt",
                    "type": "application/zip",
                },
                "Offset": 0,
                "PartialUploads": None,
                "Size": 100,
                "SizeIsDeferred": False,
                "Storage": {"Type": "filestore", "Path": file_path},
            },
        }
        with self.assertLogs(level="ERROR") as error_log:
            result = self.client_post(
                f"/tusd/hooks?secret={settings.SHARED_SECRET}",
                body,
                content_type="application/json",
                HTTP_HOOK_NAME="pre-finish",
            )
        self.assertEqual(
            error_log.output,
            [
                f"ERROR:root:error moving tusd file {file_path}: [Errno 2] No such file or directory: '{file_path}'"
            ],
        )
        self.assert_json_error(result, msg="Upload failed.")

    @use_s3_backend
    def test_s3_file_move_fails(self) -> None:
        self.login("hamlet")
        file_id = "e4b4acc5ddb8675d3af4e75a1a095bd7"
        path_id = f"tusd/{file_id}"
        create_s3_buckets(settings.S3_AUTH_UPLOADS_BUCKET)
        body = {
            "Upload": {
                "ID": file_id,
                "IsFinal": False,
                "IsPartial": False,
                "MetaData": {
                    "filename": "zulip.txt",
                    "filetype": "application/zip",
                    "name": "zulip.txt",
                    "type": "application/zip",
                },
                "Offset": 0,
                "PartialUploads": None,
                "Size": 100,
                "SizeIsDeferred": False,
                "Storage": {"Type": "s3store", "Key": path_id},
            },
        }

        with self.assertLogs(level="ERROR") as error_log:
            result = self.client_post(
                f"/tusd/hooks?secret={settings.SHARED_SECRET}",
                body,
                content_type="application/json",
                HTTP_HOOK_NAME="pre-finish",
            )
        self.assertEqual(
            error_log.output,
            [
                f"ERROR:root:error moving tusd file {path_id}: An error occurred (404) when calling the HeadObject operation: Not Found"
            ],
        )
        self.assert_json_error(result, "Upload failed.")
