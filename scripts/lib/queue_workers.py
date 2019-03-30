#!/usr/bin/env python3

import scripts.lib.setup_path_on_import
import django
from zerver.worker.queue_processors import get_active_worker_queues
import argparse
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)

os.environ['DJANGO_SETTINGS_MODULE'] = 'zproject.settings'

django.setup()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--queue-type', action='store', dest='queue_type', default=None,
                        help="Specify which types of queues to list")
    args = parser.parse_args()

    for worker in sorted(get_active_worker_queues(args.queue_type)):
        print(worker)
