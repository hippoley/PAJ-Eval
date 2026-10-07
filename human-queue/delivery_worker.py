"""Run crash-safe HumanQueue delivery jobs.

Configure one or more adapters through environment variables, then run:

    python human-queue/delivery_worker.py

Supported environment variables:
- HUMANQUEUE_DB
- HUMANQUEUE_WORKER_ID
- HUMANQUEUE_WEBHOOK_URL
- HUMANQUEUE_WEBHOOK_BEARER_TOKEN
- HUMANQUEUE_GITHUB_REPOSITORY
- HUMANQUEUE_GITHUB_TOKEN
- HUMANQUEUE_GITHUB_EVENT_TYPE
"""

from __future__ import annotations

import os
import socket
import time
from pathlib import Path

from adapters import GenericWebhookAdapter, GitHubRepositoryDispatchAdapter
from delivery import DurableDeliveryQueue, reconcile_bound_deliveries, run_delivery_once
from destinations import DestinationRegistry
from runtime import HumanQueue


ROOT = Path(__file__).resolve().parent
DEFAULT_DB = ROOT / "demo-human-queue.db"


def build_registry() -> dict[str, object]:
    registry: dict[str, object] = {}

    webhook_url = os.environ.get("HUMANQUEUE_WEBHOOK_URL")
    if webhook_url:
        adapter = GenericWebhookAdapter(
            webhook_url,
            bearer_token=os.environ.get("HUMANQUEUE_WEBHOOK_BEARER_TOKEN"),
        )
        registry[adapter.name] = adapter

    github_repository = os.environ.get("HUMANQUEUE_GITHUB_REPOSITORY")
    github_token = os.environ.get("HUMANQUEUE_GITHUB_TOKEN")
    if github_repository and github_token:
        adapter = GitHubRepositoryDispatchAdapter(
            github_repository,
            token=github_token,
            event_type=os.environ.get(
                "HUMANQUEUE_GITHUB_EVENT_TYPE",
                "humanqueue-resume",
            ),
        )
        registry[adapter.name] = adapter

    return registry


def run_worker_once(
    *,
    db: Path,
    worker_id: str,
    registry: dict[str, object],
    now: float | None = None,
):
    queue = HumanQueue(db)
    deliveries = DurableDeliveryQueue(db)
    destinations = DestinationRegistry(db)
    reconcile_bound_deliveries(queue, deliveries, destinations)
    return run_delivery_once(
        queue,
        deliveries,
        registry,
        worker=worker_id,
        now=now,
    )


def main() -> None:
    db = Path(os.environ.get("HUMANQUEUE_DB", str(DEFAULT_DB)))
    worker_id = os.environ.get(
        "HUMANQUEUE_WORKER_ID",
        f"{socket.gethostname()}-{os.getpid()}",
    )
    interval = float(os.environ.get("HUMANQUEUE_WORKER_POLL_INTERVAL", "0.5"))
    registry = build_registry()

    if not registry:
        raise SystemExit(
            "No delivery adapters configured. Set HUMANQUEUE_WEBHOOK_URL "
            "or HUMANQUEUE_GITHUB_REPOSITORY + HUMANQUEUE_GITHUB_TOKEN."
        )

    print(f"human:// delivery worker {worker_id}")
    print(f"queue db: {db}")
    print("adapters: " + ", ".join(sorted(registry)))

    try:
        while True:
            job = run_worker_once(
                db=db,
                worker_id=worker_id,
                registry=registry,
            )
            if job is None:
                time.sleep(interval)
                continue
            print(
                f"[delivery] {job.id} wait={job.wait_id} "
                f"status={job.status} attempt={job.attempt}/{job.max_attempts}"
            )
    except KeyboardInterrupt:
        print("\nworker stopped")


if __name__ == "__main__":
    main()
