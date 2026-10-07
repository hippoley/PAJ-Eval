import importlib.util
import json
import sys
import threading
import urllib.error
import urllib.request
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


runtime = load("human_queue_runtime_evidence", ROOT / "runtime.py")
checkpoint_module = load(
    "human_queue_checkpoint_evidence",
    ROOT / "audit_checkpoint.py",
)
witness_module = load(
    "human_queue_witness_evidence",
    ROOT / "audit_witness.py",
)
quorum_module = load(
    "human_queue_quorum_evidence",
    ROOT / "audit_witness_quorum.py",
)
evidence_module = load(
    "human_queue_evidence",
    ROOT / "evidence.py",
)
server_module = load(
    "human_queue_server_evidence",
    ROOT / "server.py",
)

HumanQueue = runtime.HumanQueue
AuditCheckpointSigner = checkpoint_module.AuditCheckpointSigner
InMemoryWitnessProvider = witness_module.InMemoryWitnessProvider
WitnessReceiptJournal = witness_module.WitnessReceiptJournal
WitnessQuorum = quorum_module.WitnessQuorum
build_evidence_snapshot = evidence_module.build_evidence_snapshot


def request_json(base, path):
    request = urllib.request.Request(base + path, method="GET")
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def make_decided_queue(db):
    queue = HumanQueue(db)
    item = queue.ask(
        uri="human://approve",
        title="Evidence snapshot",
        source="agent",
    )
    queue.decide(item.id, action="approve", actor="alice")
    return queue


def test_evidence_id_is_stable_across_generation_time(tmp_path):
    queue = make_decided_queue(tmp_path / "queue.db")

    first = build_evidence_snapshot(
        queue,
        generated_at=100,
    )
    second = build_evidence_snapshot(
        queue,
        generated_at=200,
    )

    assert first["schema"] == "humanqueue.evidence.v1"
    assert first["generated_at"] == 100
    assert second["generated_at"] == 200
    assert first["evidence_id"] == second["evidence_id"]
    assert first["policy_ok"] is True


def test_evidence_id_changes_when_checkpoint_state_changes(tmp_path):
    queue = make_decided_queue(tmp_path / "queue.db")

    before = build_evidence_snapshot(
        queue,
        generated_at=100,
    )
    signer = AuditCheckpointSigner(
        queue,
        tmp_path / "checkpoints.jsonl",
        key="checkpoint-secret",
    )
    signer.create(now=100)
    after = build_evidence_snapshot(
        queue,
        checkpoint_signer=signer,
        generated_at=100,
    )

    assert before["evidence_id"] != after["evidence_id"]
    assert after["checkpoint"]["configured"] is True
    assert after["checkpoint"]["latest"]["sequence"] == 1
    assert after["checkpoint"]["verification"]["ok"] is True


def test_evidence_tracks_verified_witness_receipt_without_secrets(tmp_path):
    queue = make_decided_queue(tmp_path / "queue.db")
    signer = AuditCheckpointSigner(
        queue,
        tmp_path / "checkpoints.jsonl",
        key="checkpoint-secret",
    )
    checkpoint = signer.create(now=100)
    witness = InMemoryWitnessProvider(
        witness="witness-a",
        key="witness-secret",
    )
    receipt = witness.publish(checkpoint)
    journal = WitnessReceiptJournal(
        tmp_path / "receipts.jsonl"
    )
    journal.append(receipt, provider=witness)

    snapshot = build_evidence_snapshot(
        queue,
        checkpoint_signer=signer,
        witness_provider=witness,
        witness_receipts=journal,
        generated_at=100,
    )

    assert snapshot["policy_ok"] is True
    assert snapshot["witness"]["status"]["witnessed"] is True
    assert snapshot["witness"]["receipt_count"] == 1
    raw = json.dumps(snapshot)
    assert "checkpoint-secret" not in raw
    assert "witness-secret" not in raw


def test_quorum_policy_controls_evidence_policy_ok(tmp_path):
    queue = make_decided_queue(tmp_path / "queue.db")
    signer = AuditCheckpointSigner(
        queue,
        tmp_path / "checkpoints.jsonl",
        key="checkpoint-secret",
    )
    checkpoint = signer.create(now=100)
    witness_a = InMemoryWitnessProvider(
        witness="witness-a",
        key="secret-a",
    )
    witness_b = InMemoryWitnessProvider(
        witness="witness-b",
        key="secret-b",
    )
    quorum = WitnessQuorum(
        {
            "witness-a": witness_a,
            "witness-b": witness_b,
        },
        threshold=2,
    )
    journal = WitnessReceiptJournal(
        tmp_path / "receipts.jsonl"
    )

    before = build_evidence_snapshot(
        queue,
        checkpoint_signer=signer,
        witness_receipts=journal,
        witness_quorum=quorum,
        generated_at=100,
    )
    assert before["policy_ok"] is False
    assert before["quorum"]["satisfied"] is False

    for receipt in quorum.publish(checkpoint).receipts:
        journal.append(
            receipt,
            provider=quorum.provider_for(receipt.witness),
            already_verified=True,
        )

    after = build_evidence_snapshot(
        queue,
        checkpoint_signer=signer,
        witness_receipts=journal,
        witness_quorum=quorum,
        generated_at=100,
    )
    assert after["policy_ok"] is True
    assert after["quorum"]["satisfied"] is True
    assert after["evidence_id"] != before["evidence_id"]


def test_evidence_endpoint_stays_readable_when_health_policy_fails(tmp_path):
    queue = make_decided_queue(tmp_path / "queue.db")
    signer = AuditCheckpointSigner(
        queue,
        tmp_path / "checkpoints.jsonl",
        key="checkpoint-secret",
    )
    signer.create(now=100)
    witness = InMemoryWitnessProvider(
        witness="witness-a",
        key="secret-a",
    )
    quorum = WitnessQuorum(
        {"witness-a": witness},
        threshold=1,
    )
    journal = WitnessReceiptJournal(
        tmp_path / "receipts.jsonl"
    )

    httpd = server_module.make_server(
        queue,
        host="127.0.0.1",
        port=0,
        audit_checkpoint_signer=signer,
        audit_witness_receipts=journal,
        audit_witness_quorum=quorum,
    )
    thread = threading.Thread(
        target=httpd.serve_forever,
        daemon=True,
    )
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        health_status, health = request_json(
            base,
            "/api/health",
        )
        evidence_status, evidence = request_json(
            base,
            "/api/evidence",
        )

        assert health_status == 503
        assert health["ok"] is False
        assert evidence_status == 200
        assert evidence["policy_ok"] is False
        assert evidence["quorum"]["satisfied"] is False
        assert health["evidence_id"] == evidence["evidence_id"]
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()
