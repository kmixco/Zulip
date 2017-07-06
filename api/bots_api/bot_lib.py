from __future__ import print_function

import logging
import os
import signal
import sys
import time
import re

from threading import Thread
try:
    from queue import PriorityQueue
except ImportError:  # if we're using python 2 for some reason?
    from Queue import PriorityQueue

from six.moves import configparser

if False:
    from mypy_extensions import NoReturn
from typing import Any, Optional, List, Dict
from types import ModuleType

our_dir = os.path.dirname(os.path.abspath(__file__))

# For dev setups, we can find the API in the repo itself.
if os.path.exists(os.path.join(our_dir, '../zulip')):
    sys.path.insert(0, os.path.join(our_dir, '../'))

from zulip import Client

def exit_gracefully(signum, frame):
    # type: (int, Optional[Any]) -> None
    sys.exit(0)

class RateLimit(object):
    def __init__(self, message_limit, interval_limit):
        # type: (int, int) -> None
        self.message_limit = message_limit
        self.interval_limit = interval_limit
        self.message_list = []  # type: List[float]
        self.error_message = '-----> !*!*!*MESSAGE RATE LIMIT REACHED, EXITING*!*!*! <-----\n'
        'Is your bot trapped in an infinite loop by reacting to its own messages?'

    def is_legal(self):
        # type: () -> bool
        self.message_list.append(time.time())
        if len(self.message_list) > self.message_limit:
            self.message_list.pop(0)
            time_diff = self.message_list[-1] - self.message_list[0]
            return time_diff >= self.interval_limit
        else:
            return True

    def show_error_and_exit(self):
        # type: () -> NoReturn
        logging.error(self.error_message)
        sys.exit(1)

def send_reply(message, response, email, send_message):
    # type: (Dict[str, Any], str, str, Any) -> Dict[str, Any]
    if message['type'] == 'private':
        return send_message(dict(
            type='private',
            to=[x['email'] for x in message['display_recipient'] if email != x['email']],
            content=response,
        ))
    else:
        return send_message(dict(
            type='stream',
            to=message['display_recipient'],
            subject=message['subject'],
            content=response,
        ))


class ExternalBotHandler(object):
    def __init__(self, client):
        # type: (Client) -> None
        # Only expose a subset of our Client's functionality
        user_profile = client.get_profile()
        self._rate_limit = RateLimit(20, 5)
        self._client = client
        try:
            self.full_name = user_profile['full_name']
            self.email = user_profile['email']
        except KeyError:
            logging.error('Cannot fetch user profile, make sure you have set'
                          ' up the zuliprc file correctly.')
            sys.exit(1)

    def send_message(self, message):
        # type: (Dict[str, Any]) -> Dict[str, Any]
        if self._rate_limit.is_legal():
            return self._client.send_message(message)
        else:
            self._rate_limit.show_error_and_exit()

    def send_reply(self, message, response):
        # type: (Dict[str, Any], str) -> Dict[str, Any]
        return send_reply(message, response, self.email, self.send_message)

    def update_message(self, message):
        # type: (Dict[str, Any]) -> Dict[str, Any]
        if self._rate_limit.is_legal():
            return self._client.update_message(message)
        else:
            self._rate_limit.show_error_and_exit()

    def get_config_info(self, bot_name, section=None, optional=False):
        # type: (str, Optional[str], Optional[bool]) -> Dict[str, Any]
        conf_file_path = os.path.realpath(os.path.join(
            our_dir, '..', 'bots', bot_name, bot_name + '.conf'))
        section = section or bot_name
        config = configparser.ConfigParser()
        try:
            config.readfp(open(conf_file_path))  # type: ignore
        except IOError:
            if optional:
                return dict()
            raise
        return dict(config.items(section))

class StateHandler(object):
    def __init__(self):
        # type: () -> None
        self.state = None  # type: Any

    def set_state(self, state):
        # type: (Any) -> None
        self.state = state

    def get_state(self):
        # type: () -> Any
        return self.state

#  The PriorityQueue of timers stores tuples of the format:
#  index 0: Unix time of of the event's scheduled firing time
#  index 1: 0 if the event should not repeat, the repeat interval if it should
#  index 2: The function to call when the event fires
class EventTimer(object):
    def __init__(self):
        self.timers = PriorityQueue()
        self.t = Thread(target=self.run)
        self.t.daemon = True
        self.t.start()

    def schedule(self, function, task_time, repeat=False):
        repeat_time = task_time if repeat else 0
        self.timers.put((time.time() + task_time, repeat_time, function))

    def run(self):
        while True:
            task = self.timers.get()  # Blocks until there is a task

            time.sleep(1)
            if task[0] > time.time():  # If the task isn't done, add it back
                self.timers.put(task)
                continue

            task[2]()
            if task[1]:  # If the function repeats, add it back
                self.schedule(task[2], task[1], repeat=True)

def run_message_handler_for_bot(lib_module, quiet, config_file):
    # type: (Any, bool, str) -> Any
    #
    # lib_module is of type Any, since it can contain any bot's
    # handler class. Eventually, we want bot's handler classes to
    # inherit from a common prototype specifying the handle_message
    # function.
    #
    # Make sure you set up your ~/.zuliprc
    client = Client(config_file=config_file)
    restricted_client = ExternalBotHandler(client)

    message_handler = lib_module.handler_class()
    if hasattr(message_handler, 'initialize'):
        message_handler.initialize(bot_handler=restricted_client)

    state_handler = StateHandler()
    event_timer = EventTimer()

    if not quiet:
        print(message_handler.usage())

    def extract_query_without_mention(message, client):
        # type: (Dict[str, Any], ExternalBotHandler) -> str
        """
        If the bot is the first @mention in the message, then this function returns
        the message with the bot's @mention removed.  Otherwise, it returns None.
        """
        bot_mention = r'^@(\*\*{0}\*\*)'.format(client.full_name)
        start_with_mention = re.compile(bot_mention).match(message['content'])
        if start_with_mention is None:
            return None
        query_without_mention = message['content'][len(start_with_mention.group()):]
        return query_without_mention.lstrip()

    def is_private(message, client):
        # type: (Dict[str, Any], ExternalBotHandler) -> bool
        # bot will not reply if the sender name is the same as the bot name
        # to prevent infinite loop
        if message['type'] == 'private':
            return client.full_name != message['sender_full_name']
        return False

    def handle_message(message):
        # type: (Dict[str, Any]) -> None
        logging.info('waiting for next message')

        # is_mentioned is true if the bot is mentioned at ANY position (not necessarily
        # the first @mention in the message).
        is_mentioned = message['is_mentioned']
        is_private_message = is_private(message, restricted_client)

        # Strip at-mention botname from the message
        if is_mentioned:
            # message['content'] will be None when the bot's @-mention is not at the beginning.
            # In that case, the message shall not be handled.
            message['content'] = extract_query_without_mention(message=message, client=restricted_client)
            if message['content'] is None:
                return

        if is_private_message or is_mentioned:
            message_handler.handle_message(
                message=message,
                bot_handler=restricted_client,
                state_handler=state_handler,
                event_timer=event_timer,
            )

    signal.signal(signal.SIGINT, exit_gracefully)

    logging.info('starting message handling...')
    client.call_on_each_message(handle_message)
