import importlib.util
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).parents[1] / "human-queue"
sys.path.insert(0, str(ROOT))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


runtime = load("human_queue_runtime_audit_chain", ROOT / "runtime.py")
HumanQueue = runtime.HumanQueue


def make_decided_queue(db):
    queue = HumanQueue(db)
    item = queue.ask(
        uri="human://approve",
        title="Audit integrity",
        source="agent",
    )
    queue.decide(item.id, action="approve", actor="alice")
    queue.mark_resumed(item.id, actor="worker-a")
    queue.mark_completed(item.id, actor="worker-a", success=True)
    return queue, item


def test_audit_chain_links_events_and_verifies(tmp_path):
    queue, item = make_decided_queue(tmp_path / "queue.db")

    result = queue.verify_audit_chain()
    assert result["ok"] is True
    assert result["checked"] >= 4
    assert result["head_hash"]

    events = queue.audit_events(item.id)
    assert events[0].prev_hash is None
    assert events[0].event_hash
    for previous, current in zip(events, events[1:]):
        assert current.prev_hash == previous.event_hash
        assert current.event_hash


def test_audit_chain_detects_tamper_and_restart_does_not_heal(tmp_path):
    db = tmp_path / "queue.db"
    queue, item = make_decided_queue(db)
    events = queue.audit_events(item.id)
    tampered_id = events[1].id

    with sqlite3.connect(db) as conn:
        conn.execute(
            "UPDATE audit_events SET data_json = ? WHERE id = ?",
            ('{"tampered":true}', tampered_id),
        )

    broken = queue.verify_audit_chain()
    assert broken["ok"] is False
    assert broken["broken_event_id"] == tampered_id

    reopened = HumanQueue(db)
    still_broken = reopened.verify_audit_chain()
    assert still_broken["ok"] is False
    assert still_broken["broken_event_id"] == tampered_id


def test_legacy_unhashed_audit_rows_are_backfilled_once(tmp_path):
    db = tmp_path / "queue.db"
    queue, item = make_decided_queue(db)

    with sqlite3.connect(db) as conn:
        conn.execute(
            "UPDATE audit_events SET prev_hash = NULL, event_hash = NULL"
        )

    migrated = HumanQueue(db)
    result = migrated.verify_audit_chain()
    assert result["ok"] is True

    events = migrated.audit_events(item.id)
    assert all(event.event_hash for event in events)


def test_audit_chain_detects_deleted_middle_event(tmp_path):
    db = tmp_path / "queue.db"
    queue, item = make_decided_queue(db)
    events = queue.audit_events(item.id)
    assert len(events) >= 4

    deleted_id = events[1].id
    with sqlite3.connect(db) as conn:
        conn.execute(
            "DELETE FROM audit_events WHERE id = ?",
            (deleted_id,),
        )

    broken = queue.verify_audit_chain()
    assert broken["ok"] is False
    assert broken["broken_event_id"] == events[2].id
