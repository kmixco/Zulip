import os
from typing import Any
from unittest import mock

import requests
import responses

from zerver.lib.outgoing_http import OutgoingSession
from zerver.lib.test_classes import ZulipTestCase


class RequestMockWithProxySupport(responses.RequestsMock):
    def _on_request(
        self,
        adapter: requests.adapters.HTTPAdapter,
        request: requests.PreparedRequest,
        **kwargs: Any,
    ) -> requests.Response:
        if "proxies" in kwargs and request.url:
            proxy_uri = requests.utils.select_proxy(request.url, kwargs["proxies"])
            if proxy_uri is not None:
                request = requests.Request(
                    method="GET",
                    url=f"{proxy_uri}/",
                    headers=adapter.proxy_headers(proxy_uri),
                ).prepare()
        return super()._on_request(  # type: ignore[misc]  # This is an undocumented internal API
            adapter,
            request,
            **kwargs,
        )


class RequestMockWithTimeoutAsHeader(responses.RequestsMock):
    def _on_request(
        self,
        adapter: requests.adapters.HTTPAdapter,
        request: requests.PreparedRequest,
        **kwargs: Any,
    ) -> requests.Response:
        if kwargs.get("timeout") is not None:
            request.headers["X-Timeout"] = kwargs["timeout"]
        return super()._on_request(  # type: ignore[misc]  # This is an undocumented internal API
            adapter,
            request,
            **kwargs,
        )


class TestOutgoingHttp(ZulipTestCase):
    def test_headers(self) -> None:
        with RequestMockWithProxySupport() as mock_requests:
            mock_requests.add(responses.GET, "http://example.com/")
            OutgoingSession(role="testing", timeout=1, headers={"X-Foo": "bar"}).get(
                "http://example.com/"
            )
            self.assert_length(mock_requests.calls, 1)
            headers = mock_requests.calls[0].request.headers
            # We don't see a proxy header with no proxy set
            self.assertFalse("X-Smokescreen-Role" in headers)
            self.assertEqual(headers["X-Foo"], "bar")

    @mock.patch.dict(os.environ, {"http_proxy": "http://localhost:4242"})
    def test_proxy_headers(self) -> None:
        with RequestMockWithProxySupport() as mock_requests:
            mock_requests.add(responses.GET, "http://localhost:4242/")
            OutgoingSession(role="testing", timeout=1, headers={"X-Foo": "bar"}).get(
                "http://example.com/"
            )
            self.assert_length(mock_requests.calls, 1)
            headers = mock_requests.calls[0].request.headers
            self.assertEqual(headers["X-Smokescreen-Role"], "testing")

            # We don't see the request-level headers in the proxy
            # request.  This isn't a _true_ test because we're
            # fiddling the headers above, instead of urllib3 actually
            # setting them.
            self.assertFalse("X-Foo" in headers)

    def test_timeouts(self) -> None:
        with RequestMockWithTimeoutAsHeader() as mock_requests:
            mock_requests.add(responses.GET, "http://example.com/")
            OutgoingSession(role="testing", timeout=17).get("http://example.com/")
            self.assert_length(mock_requests.calls, 1)
            self.assertEqual(mock_requests.calls[0].request.headers["X-Timeout"], 17)

        with RequestMockWithTimeoutAsHeader() as mock_requests:
            mock_requests.add(responses.GET, "http://example.com/")
            OutgoingSession(role="testing", timeout=17).get("http://example.com/", timeout=42)
            self.assert_length(mock_requests.calls, 1)
            self.assertEqual(mock_requests.calls[0].request.headers["X-Timeout"], 42)
