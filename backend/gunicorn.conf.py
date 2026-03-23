"""Gunicorn configuration file.

Only worker 0 runs the APScheduler background jobs to avoid
duplicate scheduled tasks across multiple workers.
"""

import os

bind = "0.0.0.0:5002"
workers = int(os.environ.get("GUNICORN_WORKERS", 4))
timeout = 120
worker_class = "sync"


def post_fork(server, worker):
    """Called after a worker has been forked.

    Disable the scheduler for all workers except worker 0.
    The scheduler init code in app/scheduler.py reads SCHEDULER_ENABLED
    to decide whether to start.
    """
    # worker.age starts at 1 for the first worker spawned
    if worker.age != 1:
        os.environ["SCHEDULER_ENABLED"] = "0"
    else:
        os.environ["SCHEDULER_ENABLED"] = "1"
