import importlib.util
import threading
import time
from pathlib import Path

import pytest


RUNTIME = Path(__file__).parents[1] / "human-queue" / "runtime.py"
spec = importlib.util.spec_from_file_location("human_queue_runtime", RUNTIME)
runtime = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(runtime)
HumanQueue = runtime.HumanQueue


def test_ask_is_idempotent(tmp_path):
    q = HumanQueue(tmp_path / "queue.db")
    first = q.ask(
        uri="human://approve",
        title="Deploy?",
        source="ci",
        idempotency_key="deploy-42",
    )
    second = q.ask(
        uri="human://approve",
        title="Deploy?",
        source="ci",
        idempotency_key="deploy-42",
    )
    assert first.id == second.id
    assert len(q.pending()) == 1


def test_decision_is_durable_and_conflicts_are_rejected(tmp_path):
    q = HumanQueue(tmp_path / "queue.db")
    item = q.ask(uri="human://approve", title="Delete?", source="agent")

    decided = q.decide(item.id, action="approve", actor="brook")
    assert decided.state == "approved"

    reopened = HumanQueue(tmp_path / "queue.db")
    persisted = reopened.get(item.id)
    assert persisted.decision == {"action": "approve", "actor": "brook", "value": None}
    assert reopened.pending() == []

    same = reopened.decide(item.id, action="approve", actor="brook")
    assert same.state == "approved"

    with pytest.raises(RuntimeError):
        reopened.decide(item.id, action="reject", actor="brook")


def test_blocked_process_really_resumes_after_decision(tmp_path):
    q = HumanQueue(tmp_path / "queue.db")
    item = q.ask(
        uri="human://approve",
        title="Production action?",
        source="agent",
        resume_token="step-3",
    )
    outcome = {}

    def blocked_process():
        outcome["result"] = q.wait_for_decision(item.id, timeout=2, poll_interval=0.01)

    thread = threading.Thread(target=blocked_process)
    thread.start()
    time.sleep(0.05)
    assert thread.is_alive()

    q.decide(item.id, action="approve")
    thread.join(timeout=1)

    assert not thread.is_alive()
    assert outcome["result"].state == "approved"
    assert outcome["result"].resume_token == "step-3"
