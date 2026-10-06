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

    renewed = q.claim(item.id, actor="alice", lease_seconds=0.05)
    assert renewed.claimed_by == "alice"

    time.sleep(0.08)
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


def test_audit_log_records_wait_claim_release_and_decision(tmp_path):
    q = HumanQueue(tmp_path / "queue.db")
    item = q.ask(
        uri="human://approve",
        title="Audit me",
        source="ci",
        payload={"risk": "high"},
    )
    q.claim(item.id, actor="alice", lease_seconds=1)
    q.release_claim(item.id, actor="alice")
    q.claim(item.id, actor="bob", lease_seconds=1)
    q.decide(item.id, action="approve", actor="bob")

    events = q.audit_events(item.id)
    assert [event.event_type for event in events] == [
        "WAIT_CREATED",
        "CLAIMED",
        "CLAIM_RELEASED",
        "CLAIMED",
        "DECISION_COMMITTED",
        "RESUME_REQUESTED",
    ]
    assert events[0].actor == "ci"
    assert events[-1].actor == "bob"
    assert events[-1].data["action"] == "approve"
    assert events[-1].data["state"] == "approved"


def test_idempotent_decision_replay_does_not_duplicate_audit_event(tmp_path):
    q = HumanQueue(tmp_path / "queue.db")
    item = q.ask(uri="human://approve", title="Once", source="agent")
    q.decide(item.id, action="approve", actor="alice")
    q.decide(item.id, action="approve", actor="alice")

    event_types = [event.event_type for event in q.audit_events(item.id)]
    assert event_types.count("DECISION_COMMITTED") == 1


def test_conflicting_decision_does_not_append_false_audit_event(tmp_path):
    q = HumanQueue(tmp_path / "queue.db")
    item = q.ask(uri="human://approve", title="One truth", source="agent")
    q.decide(item.id, action="approve", actor="alice")

    with pytest.raises(RuntimeError):
        q.decide(item.id, action="reject", actor="bob")

    events = q.audit_events(item.id)
    decisions = [event for event in events if event.event_type == "DECISION_COMMITTED"]
    assert len(decisions) == 1
    assert decisions[0].actor == "alice"
    assert decisions[0].data["action"] == "approve"


def test_approve_requests_resume_then_machine_acknowledges_completion(tmp_path):
    q = HumanQueue(tmp_path / "queue.db")
    item = q.ask(
        uri="human://approve",
        title="Resume?",
        source="agent",
        resume_token="step-9",
    )

    approved = q.decide(item.id, action="approve", actor="alice")
    assert approved.execution_state == "resume_requested"
    assert approved.resume_requested_at is not None

    resumed = q.mark_resumed(item.id, actor="agent")
    assert resumed.execution_state == "resumed"
    assert resumed.resumed_at is not None

    completed = q.mark_completed(
        item.id,
        actor="agent",
        success=True,
        detail="done",
    )
    assert completed.execution_state == "completed"
    assert completed.completed_at is not None

    assert [event.event_type for event in q.audit_events(item.id)] == [
        "WAIT_CREATED",
        "DECISION_COMMITTED",
        "RESUME_REQUESTED",
        "PROCESS_RESUMED",
        "PROCESS_COMPLETED",
    ]


def test_rejected_wait_never_requests_or_allows_resume(tmp_path):
    q = HumanQueue(tmp_path / "queue.db")
    item = q.ask(uri="human://approve", title="Do not run?", source="agent")
    rejected = q.decide(item.id, action="reject", actor="alice")

    assert rejected.execution_state is None
    assert "RESUME_REQUESTED" not in [
        event.event_type for event in q.audit_events(item.id)
    ]

    with pytest.raises(RuntimeError):
        q.mark_resumed(item.id, actor="agent")


def test_completion_requires_resume_and_terminal_result_is_idempotent(tmp_path):
    q = HumanQueue(tmp_path / "queue.db")
    item = q.ask(uri="human://approve", title="Order matters", source="agent")
    q.decide(item.id, action="approve", actor="alice")

    with pytest.raises(RuntimeError):
        q.mark_completed(item.id, actor="agent", success=True)

    q.mark_resumed(item.id, actor="agent")
    first = q.mark_completed(item.id, actor="agent", success=False, detail="boom")
    second = q.mark_completed(item.id, actor="agent", success=False, detail="ignored replay")

    assert first.execution_state == "failed"
    assert second.execution_state == "failed"
    events = q.audit_events(item.id)
    assert [e.event_type for e in events].count("PROCESS_FAILED") == 1

    with pytest.raises(RuntimeError):
        q.mark_completed(item.id, actor="agent", success=True)


def test_mark_resumed_is_idempotent(tmp_path):
    q = HumanQueue(tmp_path / "queue.db")
    item = q.ask(uri="human://approve", title="Resume once", source="agent")
    q.decide(item.id, action="approve", actor="alice")

    first = q.mark_resumed(item.id, actor="agent")
    second = q.mark_resumed(item.id, actor="agent")

    assert first.execution_state == "resumed"
    assert second.execution_state == "resumed"
    assert [e.event_type for e in q.audit_events(item.id)].count("PROCESS_RESUMED") == 1
