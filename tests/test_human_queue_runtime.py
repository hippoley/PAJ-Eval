import importlib.util
import sys
import threading
import time
from pathlib import Path

import pytest


RUNTIME = Path(__file__).parents[1] / "human-queue" / "runtime.py"
spec = importlib.util.spec_from_file_location("human_queue_runtime", RUNTIME)
runtime = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = runtime
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


def test_concurrent_idempotent_ask_converges_to_one_wait(tmp_path):
    q = HumanQueue(tmp_path / "queue.db")
    ids = []
    errors = []
    barrier = threading.Barrier(8)

    def producer():
        try:
            barrier.wait()
            item = q.ask(
                uri="human://approve",
                title="Deploy once?",
                source="ci",
                idempotency_key="deploy-race",
            )
            ids.append(item.id)
        except Exception as exc:  # pragma: no cover - diagnostic path
            errors.append(exc)

    threads = [threading.Thread(target=producer) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=2)

    assert errors == []
    assert len(ids) == 8
    assert len(set(ids)) == 1
    assert len(q.pending()) == 1


def test_conflicting_concurrent_decisions_have_one_winner(tmp_path):
    q = HumanQueue(tmp_path / "queue.db")
    item = q.ask(uri="human://approve", title="One winner?", source="agent")
    outcomes = []
    barrier = threading.Barrier(2)

    def decide(action):
        barrier.wait()
        try:
            result = q.decide(item.id, action=action, actor=action)
            outcomes.append(("ok", result.state))
        except RuntimeError:
            outcomes.append(("conflict", action))

    threads = [
        threading.Thread(target=decide, args=("approve",)),
        threading.Thread(target=decide, args=("reject",)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=2)

    assert sorted(kind for kind, _ in outcomes) == ["conflict", "ok"]
    assert q.get(item.id).state in {"approved", "rejected"}


def test_claim_lease_blocks_other_actor_until_expiry(tmp_path):
    q = HumanQueue(tmp_path / "queue.db")
    item = q.ask(uri="human://review", title="Review?", source="agent")

    first = q.claim(item.id, actor="alice", lease_seconds=0.1)
    assert first.claimed_by == "alice"
    assert first.claim_expires_at is not None

    with pytest.raises(RuntimeError):
        q.claim(item.id, actor="bob", lease_seconds=1)

    renewed = q.claim(item.id, actor="alice", lease_seconds=1)
    assert renewed.claimed_by == "alice"

    time.sleep(0.12)
    taken = q.claim(item.id, actor="bob", lease_seconds=1)
    assert taken.claimed_by == "bob"


def test_release_claim_requires_owner(tmp_path):
    q = HumanQueue(tmp_path / "queue.db")
    item = q.ask(uri="human://review", title="Review?", source="agent")
    q.claim(item.id, actor="alice", lease_seconds=1)

    with pytest.raises(RuntimeError):
        q.release_claim(item.id, actor="bob")

    released = q.release_claim(item.id, actor="alice")
    assert released.claimed_by is None
    assert released.claim_expires_at is None
