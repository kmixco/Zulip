import logging
import random
import string
import ujson

from django.conf import settings
from django.contrib.auth import SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY
from django.middleware.csrf import _get_new_csrf_token
from importlib import import_module
from tornado.ioloop import IOLoop
from tornado import gen
from tornado.httpclient import HTTPRequest
from tornado.websocket import websocket_connect, WebSocketClientConnection
from six.moves.urllib.parse import urlparse
from six.moves import range


from zerver.models import UserProfile

from typing import Any, Callable, Dict, Generator, Iterable, Optional


class WebsocketClient(object):
    def __init__(self, host_url, auth_email, queue_id, run_on_start, validate_ssl=True,
                 **run_kwargs):
        # type: (str, str, str, Callable, bool, **Any) -> None
        """
        :param host_url: Websocket connection host url.
        :param auth_email: User email for websocket authentication.
        :param queue_id: Queue ID.
        :param run_on_start:  Method to launch after websocket connection start.
        :param validate_ssl: SSL certificate validation.
        :param run_kwargs: Arguments for 'run_on_start' method.
        """
        self.validate_ssl = validate_ssl
        self.user_profile = UserProfile.objects.filter(email=auth_email).first()
        self.request_id_number = 0
        self.parsed_host_url = urlparse(host_url)
        self.websocket_auth_data = self._login()
        self.ioloop_instance = IOLoop.instance()
        self.run_on_start = run_on_start
        self.run_kwargs = run_kwargs
        self.scheme_dict = {'http': 'ws', 'https': 'wss'}
        self.ws = None  # type: Optional[WebSocketClientConnection]
        self.queue_id = queue_id

    def _login(self):
        # type: () -> Dict[str,str]

        # Ideally, we'd migrate this to use API auth instead of
        # stealing cookies, but this works for now.
        auth_backend = settings.AUTHENTICATION_BACKENDS[0]
        session_auth_hash = self.user_profile.get_session_auth_hash()
        engine = import_module(settings.SESSION_ENGINE)
        session = engine.SessionStore() # type: ignore # import_module
        session[SESSION_KEY] = self.user_profile._meta.pk.value_to_string(self.user_profile)
        session[BACKEND_SESSION_KEY] = auth_backend
        session[HASH_SESSION_KEY] = session_auth_hash
        session.save()
        return {
            settings.SESSION_COOKIE_NAME: session.session_key,
            settings.CSRF_COOKIE_NAME: _get_new_csrf_token()}

    @property
    def _cookie_header(self):
        # type: () -> str
        return ';'.join(
            ["{}={}".format(name, value) for name, value in self.websocket_auth_data.items()])

    @property
    def _sockjs_url(self):
        # type: () -> str
        sockjs_server = random.randint(100, 999)
        sockjs_session = ''.join(
            random.choice(string.ascii_lowercase + string.digits) for _ in range(8))
        return "/sockjs/{}/{}/websocket".format(sockjs_server, sockjs_session)

    @gen.coroutine
    def _websocket_auth(self):
        # type: () -> Generator[str, str, None]
        message = {
            "req_id": self._get_request_id(),
            "type": "auth",
            "request": {
                "csrf_token": self.websocket_auth_data.get(settings.CSRF_COOKIE_NAME),
                "queue_id": self.queue_id,
                "status_inquiries": []
            }
        }
        auth_frame_str = ujson.dumps(message)
        self.ws.write_message(ujson.dumps([auth_frame_str]))
        response_ack = yield self.ws.read_message()
        response_message = yield self.ws.read_message()
        raise gen.Return([response_ack, response_message])

    @gen.engine
    def connect(self):
        # type: () -> Generator[str, WebSocketClientConnection, None]
        try:
            request = HTTPRequest(url=self._get_websocket_url(), validate_cert=self.validate_ssl)
            request.headers.add('Cookie', self._cookie_header)
            self.ws = yield websocket_connect(request)
            yield self.ws.read_message()
            yield self._websocket_auth()
            self.run_on_start(self, **self.run_kwargs)
        except Exception as e:
            logging.exception(str(e))
            IOLoop.instance().stop()
        IOLoop.instance().stop()

    @gen.coroutine
    def send_message(self, client, type, subject, stream, private_message_recepient, content=""):
        # type: (str, str, str, str, str, str) -> Generator[str, WebSocketClientConnection, None]
        user_message = {
            "req_id": self._get_request_id(),
            "type": "request",
            "request": {
                "client": client,
                "type": type,
                "subject": subject,
                "stream": stream,
                "private_message_recipient": private_message_recepient,
                "content": content,
                "sender_id": self.user_profile.id,
                "queue_id": self.queue_id,
                "to": ujson.dumps([private_message_recepient]),
                "reply_to": self.user_profile.email,
                "local_id": -1
            }
        }
        self.ws.write_message(ujson.dumps([ujson.dumps(user_message)]))
        response_ack = yield self.ws.read_message()
        response_message = yield self.ws.read_message()
        raise gen.Return([response_ack, response_message])

    def run(self):
        # type: () -> None
        """Start websocket connection"""
        self.ioloop_instance.add_callback(self.connect)
        self.ioloop_instance.start()

    def _get_websocket_url(self):
        # type: () -> str
        return '{}://{}{}'.format(self.scheme_dict[self.parsed_host_url.scheme],
                                  self.parsed_host_url.netloc, self._sockjs_url)

    def _get_request_id(self):
        # type: () -> Iterable[str]
        self.request_id_number += 1
        return ':'.join((self.queue_id, str(self.request_id_number)))
