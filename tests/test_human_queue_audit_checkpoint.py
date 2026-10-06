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


def test_checkpoint_key_rotation_keeps_old_and_new_checkpoints_verifiable(tmp_path):
    db = tmp_path / "queue.db"
    checkpoint_path = tmp_path / "audit-checkpoints.jsonl"
    queue, _ = make_queue(db)

    v1 = AuditCheckpointSigner(
        queue,
        checkpoint_path,
        keys={"v1": "secret-v1", "v2": "secret-v2"},
        signing_key_id="v1",
    )
    first = v1.create(now=100)
    assert first.key_id == "v1"

    item = queue.ask(
        uri="human://approve",
        title="Rotate checkpoint key",
        source="agent",
    )
    queue.decide(item.id, action="approve", actor="alice")

    v2 = AuditCheckpointSigner(
        queue,
        checkpoint_path,
        keys={"v1": "secret-v1", "v2": "secret-v2"},
        signing_key_id="v2",
    )
    second = v2.create(now=200)
    assert second.key_id == "v2"
    assert second.previous_signature == first.signature

    verified = v2.verify()
    assert verified["ok"] is True
    assert verified["checkpoint_count"] == 2
    assert verified["latest"]["key_id"] == "v2"


def test_checkpoint_verification_fails_if_historical_key_is_removed(tmp_path):
    db = tmp_path / "queue.db"
    checkpoint_path = tmp_path / "audit-checkpoints.jsonl"
    queue, _ = make_queue(db)

    signer = AuditCheckpointSigner(
        queue,
        checkpoint_path,
        keys={"v1": "secret-v1", "v2": "secret-v2"},
        signing_key_id="v1",
    )
    signer.create(now=100)

    without_old_key = AuditCheckpointSigner(
        queue,
        checkpoint_path,
        keys={"v2": "secret-v2"},
        signing_key_id="v2",
    )
    result = without_old_key.verify()
    assert result["ok"] is False
    assert result["reason"] == "unknown_checkpoint_key_id"
    assert result["key_id"] == "v1"


def test_checkpoint_env_keyring_selects_active_signing_key(tmp_path, monkeypatch):
    db = tmp_path / "queue.db"
    checkpoint_path = tmp_path / "audit-checkpoints.jsonl"
    queue, _ = make_queue(db)

    monkeypatch.setenv(
        "HUMANQUEUE_AUDIT_CHECKPOINT_FILE",
        str(checkpoint_path),
    )
    monkeypatch.setenv(
        "HUMANQUEUE_AUDIT_CHECKPOINT_KEYS",
        '{"v1":"secret-v1","v2":"secret-v2"}',
    )
    monkeypatch.setenv(
        "HUMANQUEUE_AUDIT_CHECKPOINT_SIGNING_KEY_ID",
        "v2",
    )

    signer = AuditCheckpointSigner.from_env(queue)
    assert signer is not None
    checkpoint = signer.create(now=100)
    assert checkpoint.key_id == "v2"


def test_checkpoint_env_keyring_requires_active_key_id(tmp_path, monkeypatch):
    queue, _ = make_queue(tmp_path / "queue.db")
    monkeypatch.setenv(
        "HUMANQUEUE_AUDIT_CHECKPOINT_FILE",
        str(tmp_path / "audit-checkpoints.jsonl"),
    )
    monkeypatch.setenv(
        "HUMANQUEUE_AUDIT_CHECKPOINT_KEYS",
        '{"v1":"secret-v1"}',
    )
    monkeypatch.delenv(
        "HUMANQUEUE_AUDIT_CHECKPOINT_SIGNING_KEY_ID",
        raising=False,
    )

    try:
        AuditCheckpointSigner.from_env(queue)
    except ValueError as exc:
        assert "SIGNING_KEY_ID" in str(exc)
    else:
        raise AssertionError("checkpoint keyring accepted without signing key id")


def test_checkpoint_sequence_floor_detects_tail_rollback(tmp_path):
    db = tmp_path / "queue.db"
    checkpoint_path = tmp_path / "audit-checkpoints.jsonl"
    queue, _ = make_queue(db)

    signer = AuditCheckpointSigner(
        queue,
        checkpoint_path,
        keys={"v1": "secret-v1"},
        signing_key_id="v1",
    )
    signer.create(now=100)

    item = queue.ask(
        uri="human://approve",
        title="Second anchored checkpoint",
        source="agent",
    )
    queue.decide(item.id, action="approve", actor="alice")
    signer.create(now=200)

    lines = checkpoint_path.read_text().splitlines()
    assert len(lines) == 2
    checkpoint_path.write_text(lines[0] + "\n")

    verifier = AuditCheckpointSigner(
        queue,
        checkpoint_path,
        keys={"v1": "secret-v1"},
        signing_key_id="v1",
        minimum_sequence=2,
    )
    result = verifier.verify()
    assert result["ok"] is False
    assert result["reason"] == "checkpoint_rollback_detected"
    assert result["checkpoint_count"] == 1
    assert result["minimum_sequence"] == 2


def test_checkpoint_env_loads_sequence_floor(tmp_path, monkeypatch):
    queue, _ = make_queue(tmp_path / "queue.db")
    monkeypatch.setenv(
        "HUMANQUEUE_AUDIT_CHECKPOINT_FILE",
        str(tmp_path / "audit-checkpoints.jsonl"),
    )
    monkeypatch.setenv(
        "HUMANQUEUE_AUDIT_CHECKPOINT_KEYS",
        '{"v1":"secret-v1"}',
    )
    monkeypatch.setenv(
        "HUMANQUEUE_AUDIT_CHECKPOINT_SIGNING_KEY_ID",
        "v1",
    )
    monkeypatch.setenv(
        "HUMANQUEUE_AUDIT_CHECKPOINT_MIN_SEQUENCE",
        "7",
    )

    signer = AuditCheckpointSigner.from_env(queue)
    assert signer is not None
    assert signer.minimum_sequence == 7


def test_health_fails_when_signed_checkpoint_is_tampered(tmp_path):
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
    row["event_count"] += 1
    checkpoint_path.write_text(json.dumps(row) + "\n")

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
        status, health = request_json(base, "/api/health")
        assert status == 503
        assert health["ok"] is False
        assert health["audit_chain"]["ok"] is True
        assert health["audit_checkpoint"]["ok"] is False
        assert health["audit_checkpoint"]["reason"] == "invalid_checkpoint_signature"
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_health_fails_when_local_audit_chain_is_tampered(tmp_path):
    db = tmp_path / "queue.db"
    queue, item = make_queue(db)

    with sqlite3.connect(db) as conn:
        event_id = queue.audit_events(item.id)[1].id
        conn.execute(
            "UPDATE audit_events SET actor = ? WHERE id = ?",
            ("mallory", event_id),
        )

    httpd = server_module.make_server(
        queue,
        host="127.0.0.1",
        port=0,
    )
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        status, health = request_json(base, "/api/health")
        assert status == 503
        assert health["ok"] is False
        assert health["audit_chain"]["ok"] is False
        assert health["audit_checkpoint"]["configured"] is False
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_checkpoint_file_cannot_be_same_path_as_database(tmp_path):
    db = tmp_path / "queue.db"
    queue, _ = make_queue(db)

    try:
        AuditCheckpointSigner(
            queue,
            db,
            key="checkpoint-secret",
        )
    except ValueError as exc:
        assert "separate from the SQLite database" in str(exc)
    else:
        raise AssertionError("checkpoint signer accepted database as checkpoint file")


def test_checkpoint_keyring_rejects_duplicate_secrets(tmp_path):
    queue, _ = make_queue(tmp_path / "queue.db")
    try:
        AuditCheckpointSigner(
            queue,
            tmp_path / "audit-checkpoints.jsonl",
            keys={"v1": "same-secret", "v2": "same-secret"},
            signing_key_id="v2",
        )
    except ValueError as exc:
        assert "must be unique" in str(exc)
    else:
        raise AssertionError("duplicate checkpoint signing secrets accepted")


def test_checkpoint_cli_create_and_verify_without_http_server(
    tmp_path,
    monkeypatch,
    capsys,
):
    db = tmp_path / "queue.db"
    checkpoint_path = tmp_path / "audit-checkpoints.jsonl"
    make_queue(db)

    monkeypatch.setenv(
        "HUMANQUEUE_AUDIT_CHECKPOINT_FILE",
        str(checkpoint_path),
    )
    monkeypatch.setenv(
        "HUMANQUEUE_AUDIT_CHECKPOINT_KEY",
        "checkpoint-secret",
    )
    monkeypatch.setenv(
        "HUMANQUEUE_AUDIT_CHECKPOINT_KEY_ID",
        "cli-key",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        ["audit_checkpoint.py", "--db", str(db), "create"],
    )
    checkpoint_module.main()
    created = json.loads(capsys.readouterr().out)
    assert created["sequence"] == 1
    assert created["key_id"] == "cli-key"

    monkeypatch.setattr(
        sys,
        "argv",
        ["audit_checkpoint.py", "--db", str(db), "verify"],
    )
    checkpoint_module.main()
    verified = json.loads(capsys.readouterr().out)
    assert verified["ok"] is True
    assert verified["anchored"] is True
