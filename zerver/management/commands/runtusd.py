import hmac
import os
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser


def set_query_parameter(url: str, param_name: str, param_value: str) -> str:
    scheme, netloc, path, query_string, fragment = urlsplit(url)
    query_params = parse_qs(query_string)
    query_params[param_name] = [param_value]
    new_query_string = urlencode(query_params, doseq=True)

    return urlunsplit((scheme, netloc, path, new_query_string, fragment))


class Command(BaseCommand):
    help = """Starts the tusd Server"""

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("port", help="[Port to bind HTTP server to]", type=int)
        parser.add_argument(
            "hooks_http", help="[An HTTP endpoint to which hook events will be sent to]"
        )

    def handle(self, *args: Any, **options: Any) -> None:
        port = options["port"]
        hooks_http = options["hooks_http"]
        shared_secret: str = settings.SHARED_SECRET
        shared_secret_bytes = shared_secret.encode("utf-8")
        encrypted_shared_secret = hmac.new(
            shared_secret_bytes, shared_secret_bytes, digestmod="sha256"
        ).hexdigest()
        hooks_http = set_query_parameter(hooks_http, "secret", encrypted_shared_secret)
        tusd_args = [
            "tusd",
            f"-hooks-http={hooks_http}",
            "-base-path=/chunk-upload/",
            "--hooks-enabled-events=pre-create,pre-finish",
            f"-port={port}",
            "-host=127.0.0.1",
            "-hooks-http-forward-headers=Cookie,Authorization",
            "-behind-proxy",
            "-verbose",
        ]
        env_vars = os.environ.copy()
        if settings.LOCAL_UPLOADS_DIR is not None:
            tusd_args.append(f"-upload-dir={settings.LOCAL_UPLOADS_DIR}/tusd")
        else:
            tusd_args.append(f"-s3-bucket={settings.S3_AUTH_UPLOADS_BUCKET}")
            tusd_args.append("-s3-object-prefix=tusd")
            assert settings.S3_KEY is not None
            assert settings.S3_SECRET_KEY is not None
            assert settings.S3_REGION is not None
            env_vars["AWS_ACCESS_KEY_ID"] = settings.S3_KEY
            env_vars["AWS_SECRET_ACCESS_KEY"] = settings.S3_SECRET_KEY
            env_vars["AWS_REGION"] = settings.S3_REGION
        os.execvpe("tusd", tusd_args, env_vars)
