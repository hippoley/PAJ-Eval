import importlib.util
import json
import sqlite3
import sys
import threading
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


runtime = load("human_queue_runtime_checkpoint", ROOT / "runtime.py")
checkpoint_module = load(
    "human_queue_audit_checkpoint",
    ROOT / "audit_checkpoint.py",
)
server_module = load("human_queue_server_checkpoint", ROOT / "server.py")

HumanQueue = runtime.HumanQueue
AuditCheckpointSigner = checkpoint_module.AuditCheckpointSigner


def make_queue(db):
    queue = HumanQueue(db)
    item = queue.ask(
        uri="human://approve",
        title="Checkpoint audit",
        source="agent",
    )
    queue.decide(item.id, action="approve", actor="alice")
    queue.mark_resumed(item.id, actor="worker-a")
    queue.mark_completed(item.id, actor="worker-a", success=True)
    return queue, item


def request_json(base, path, *, method="GET", body=None, headers=None):
    import urllib.error
    import urllib.request

    data = None
    if body is not None:
        data = json.dumps(body).encode()
    request = urllib.request.Request(
        base + path,
        method=method,
        data=data,
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def _rewrite_chain_after_tamper(db):
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, wait_id, event_type, actor, created_at, data_json
              FROM audit_events
             ORDER BY id
            """
        ).fetchall()
        prev_hash = None
        for row in rows:
            event_hash = HumanQueue._audit_hash(
                event_id=row["id"],
                wait_id=row["wait_id"],
                event_type=row["event_type"],
                actor=row["actor"],
                created_at=row["created_at"],
                data_json=row["data_json"],
                prev_hash=prev_hash,
            )
            conn.execute(
                """
                UPDATE audit_events
                   SET prev_hash = ?, event_hash = ?
                 WHERE id = ?
                """,
                (prev_hash, event_hash, row["id"]),
            )
            prev_hash = event_hash


def test_signed_checkpoint_verifies_and_secret_is_not_persisted(tmp_path):
    db = tmp_path / "queue.db"
    checkpoint_path = tmp_path / "audit-checkpoints.jsonl"
    queue, _ = make_queue(db)
    signer = AuditCheckpointSigner(
        queue,
        checkpoint_path,
        key="checkpoint-secret",
        key_id="audit-key-v1",
    )

    checkpoint = signer.create(now=100)
    assert checkpoint.sequence == 1
    assert checkpoint.event_count >= 4
    assert checkpoint.head_hash
    assert checkpoint.signature

    result = signer.verify()
    assert result["ok"] is True
    assert result["anchored"] is True
    assert result["checkpoint_count"] == 1
    assert result["latest"]["key_id"] == "audit-key-v1"

    raw = checkpoint_path.read_text()
    assert "checkpoint-secret" not in raw


def test_checkpoint_detects_fully_rehashed_database_history(tmp_path):
    db = tmp_path / "queue.db"
    checkpoint_path = tmp_path / "audit-checkpoints.jsonl"
    queue, item = make_queue(db)
    signer = AuditCheckpointSigner(
        queue,
        checkpoint_path,
        key="checkpoint-secret",
    )
    signer.create(now=100)

    with sqlite3.connect(db) as conn:
        event_id = queue.audit_events(item.id)[1].id
        conn.execute(
            "UPDATE audit_events SET data_json = ? WHERE id = ?",
            ('{"forged":true}', event_id),
        )

    assert queue.verify_audit_chain()["ok"] is False

    # Simulate an attacker who knows the public chaining algorithm and rewrites
    # every later local hash, but does not possess the checkpoint signing key.
    _rewrite_chain_after_tamper(db)
    assert queue.verify_audit_chain()["ok"] is True

    anchored = signer.verify()
    assert anchored["ok"] is False
    assert anchored["reason"] in {
        "audit_head_mismatch_at_checkpoint",
        "audit_checkpoint_boundary_mismatch",
    }


def test_checkpoint_file_tamper_is_detected_and_blocks_append(tmp_path):
    db = tmp_path / "queue.db"
    checkpoint_path = tmp_path / "audit-checkpoints.jsonl"
    queue, _ = make_queue(db)
    signer = AuditCheckpointSigner(
        queue,
        checkpoint_path,
        key="checkpoint-secret",
    )
    signer.create(now=100)

    row = json.loads(checkpoint_path.read_text().strip())
    row["head_hash"] = "0" * 64
    checkpoint_path.write_text(json.dumps(row) + "\n")

    result = signer.verify()
    assert result["ok"] is False
    assert result["reason"] == "invalid_checkpoint_signature"

    try:
        signer.create(now=200)
    except RuntimeError as exc:
        assert "invalid audit checkpoint chain" in str(exc)
    else:
        raise AssertionError("tampered checkpoint chain accepted append")


def test_checkpoint_chain_detects_deleted_first_checkpoint(tmp_path):
    db = tmp_path / "queue.db"
    checkpoint_path = tmp_path / "audit-checkpoints.jsonl"
    queue, _ = make_queue(db)
    signer = AuditCheckpointSigner(
        queue,
        checkpoint_path,
        key="checkpoint-secret",
    )
    signer.create(now=100)

    item = queue.ask(
        uri="human://approve",
        title="Second checkpoint",
        source="agent",
    )
    queue.decide(item.id, action="approve", actor="alice")
    signer.create(now=200)

    lines = checkpoint_path.read_text().splitlines()
    assert len(lines) == 2
    checkpoint_path.write_text(lines[1] + "\n")

    result = signer.verify()
    assert result["ok"] is False
    assert result["reason"] == "checkpoint_sequence_gap"


def test_checkpoint_remains_valid_when_audit_advances(tmp_path):
    db = tmp_path / "queue.db"
    checkpoint_path = tmp_path / "audit-checkpoints.jsonl"
    queue, _ = make_queue(db)
    signer = AuditCheckpointSigner(
        queue,
        checkpoint_path,
        key="checkpoint-secret",
    )
    first = signer.create(now=100)

    item = queue.ask(
        uri="human://approve",
        title="Audit advances",
        source="agent",
    )
    queue.decide(item.id, action="approve", actor="alice")

    result = signer.verify()
    assert result["ok"] is True
    assert result["latest"]["head_hash"] == first.head_hash
    assert result["audit"]["checked"] > first.event_count


def test_http_checkpoint_create_and_verify(tmp_path):
    db = tmp_path / "queue.db"
    checkpoint_path = tmp_path / "audit-checkpoints.jsonl"
    queue, _ = make_queue(db)
    signer = AuditCheckpointSigner(
        queue,
        checkpoint_path,
        key="checkpoint-secret",
        key_id="http-key",
    )
    httpd = server_module.make_server(
        queue,
        host="127.0.0.1",
        port=0,
        audit_checkpoint_signer=signer,
    )
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        status, created = request_json(
            base,
            "/api/audit/checkpoint",
            method="POST",
            body={"actor": "auditor"},
        )
        assert status == 201
        assert created["checkpoint"]["key_id"] == "http-key"

        status, verified = request_json(
            base,
            "/api/audit/checkpoint/verify",
        )
        assert status == 200
        assert verified["ok"] is True
        assert verified["anchored"] is True
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()
