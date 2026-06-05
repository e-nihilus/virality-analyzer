#!/usr/bin/env python
"""Standalone RQ worker for Aurea analysis jobs.

Usage:
    python -m backend.run_worker

Requires Redis running and AUREA_QUEUE_BACKEND=redis.
"""

from __future__ import annotations

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("aurea.worker")

try:
    from redis import Redis
    from rq import Worker, Queue
except ImportError:
    logger.error("redis and rq packages are required: pip install redis rq")
    sys.exit(1)

from app.core.config import settings


def main() -> None:
    if settings.queue_backend != "redis":
        logger.error(
            "AUREA_QUEUE_BACKEND is '%s', expected 'redis'. "
            "Set AUREA_QUEUE_BACKEND=redis to use the RQ worker.",
            settings.queue_backend,
        )
        sys.exit(1)

    conn = Redis.from_url(settings.redis_url)
    try:
        conn.ping()
    except Exception:
        logger.error("Cannot connect to Redis at %s", settings.redis_url)
        sys.exit(1)

    queues = [Queue("aurea-analysis", connection=conn)]
    logger.info("Starting Aurea RQ worker — queue: aurea-analysis, redis: %s", settings.redis_url)

    worker = Worker(queues, connection=conn, name="aurea-worker")
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
