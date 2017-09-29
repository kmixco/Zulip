
from typing import Any

from argparse import ArgumentParser
from django.core.management.base import BaseCommand
from django.core.management import CommandError
from zerver.lib.queue import SimpleQueueClient
from zerver.worker.queue_processors import get_active_worker_queues

class Command(BaseCommand):
    def add_arguments(self, parser):
        # type: (ArgumentParser) -> None
        parser.add_argument(dest="queue_name", type=str, nargs='?',
                            help="queue to purge", default=None)
        parser.add_argument('--all', dest="all", action="store_true",
                            default=False, help="purge all queues")

    help = "Discards all messages from the given queue"

    def handle(self, *args, **options):
        # type: (*Any, **str) -> None
        def purge_queue(queue_name):
            # type: (str) -> None
            queue = SimpleQueueClient()
            queue.ensure_queue(queue_name, lambda: None)
            queue.channel.queue_purge(queue_name)

        if options['all']:
            for queue_name in get_active_worker_queues():
                purge_queue(queue_name)
            print("All queues purged")
        elif not options['queue_name']:
            raise CommandError("Missing queue_name argument!")
        else:
            queue_name = options['queue_name']
            if queue_name not in get_active_worker_queues():
                raise CommandError("Unknown queue %s" % (queue_name,))

            print("Purging queue %s" % (queue_name,))
            purge_queue(queue_name)

        print("Done")
