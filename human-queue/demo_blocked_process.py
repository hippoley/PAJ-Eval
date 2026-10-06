"""Two-terminal HumanQueue demo.

Terminal A:
    python human-queue/demo_blocked_process.py producer

Terminal B:
    python human-queue/demo_blocked_process.py human
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running this file directly despite the hyphenated parent directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from runtime import HumanQueue  # noqa: E402


DB = Path(__file__).with_name("demo-human-queue.db")


def producer() -> None:
    q = HumanQueue(DB)
    print("[agent] preparing production cache cleanup")
    print("[agent] 1,842 stale keys found")
    item = q.ask(
        uri="human://approve",
        title="Delete 1,842 stale production cache keys?",
        source="demo-agent",
        idempotency_key="demo-cache-cleanup-v1",
        resume_token="cleanup-step-3",
        payload={"keys": 1842, "environment": "production"},
    )
    print(f"[agent] WAITING_FOR_HUMAN {item.id}")
    print("[agent] open another terminal and run: ... demo_blocked_process.py human")
    result = q.wait_for_decision(item.id)
    if result.decision and result.decision["action"] == "approve":
        print("[agent] RESUMED cleanup-step-3")
        print("[agent] deleting keys ... done")
        print("[agent] WORKFLOW_COMPLETE")
    else:
        print(f"[agent] STOPPED decision={result.decision}")


def human() -> None:
    q = HumanQueue(DB)
    waiting = q.pending()
    if not waiting:
        print("[human] no pending waits")
        return
    for index, item in enumerate(waiting, 1):
        print(f"{index}. {item.title} [{item.uri}] from {item.source}")
    selected = waiting[0]
    answer = input("Decision (approve/reject): ").strip().lower()
    if answer not in {"approve", "reject"}:
        raise SystemExit("Choose approve or reject")
    result = q.decide(selected.id, action=answer, actor="terminal-human")
    print(f"[human] {result.id} -> {result.state}")
    print("[human] original process can now resume")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "producer":
        producer()
    elif mode == "human":
        human()
    else:
        raise SystemExit("usage: demo_blocked_process.py [producer|human]")
