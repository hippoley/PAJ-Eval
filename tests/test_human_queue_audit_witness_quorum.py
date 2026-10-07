import importlib.util
import json
import threading
import urllib.error
import urllib.request
import sys
from dataclasses import replace
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


runtime = load("human_queue_runtime_witness_quorum", ROOT / "runtime.py")
checkpoint_module = load(
    "human_queue_checkpoint_witness_quorum",
    ROOT / "audit_checkpoint.py",
)
witness_module = load(
    "human_queue_witness_quorum_client",
    ROOT / "audit_witness.py",
)
quorum_module = load(
    "human_queue_witness_quorum",
    ROOT / "audit_witness_quorum.py",
)
server_module = load(
    "human_queue_server_witness_quorum",
    ROOT / "server.py",
)

HumanQueue = runtime.HumanQueue
AuditCheckpointSigner = checkpoint_module.AuditCheckpointSigner
InMemoryWitnessProvider = witness_module.InMemoryWitnessProvider
WitnessReceiptJournal = witness_module.WitnessReceiptJournal
WitnessQuorum = quorum_module.WitnessQuorum
load_witness_quorum = quorum_module.load_witness_quorum


def make_checkpoint(tmp_path):
    queue = HumanQueue(tmp_path / "queue.db")
    item = queue.ask(
        uri="human://approve",
        title="Quorum checkpoint",
        source="agent",
    )
    queue.decide(item.id, action="approve", actor="alice")
    signer = AuditCheckpointSigner(
        queue,
        tmp_path / "checkpoints.jsonl",
        key="checkpoint-secret",
    )
    return signer.create(now=100)


class FailingWitness:
    def publish(self, checkpoint):
        raise RuntimeError("witness unavailable")

    def verify(self, receipt):
        raise RuntimeError("witness unavailable")


def test_two_of_three_witnesses_can_satisfy_quorum(tmp_path):
    checkpoint = make_checkpoint(tmp_path)
    quorum = WitnessQuorum(
        {
            "witness-a": InMemoryWitnessProvider(
                witness="witness-a",
                key="secret-a",
            ),
            "witness-b": InMemoryWitnessProvider(
                witness="witness-b",
                key="secret-b",
            ),
            "witness-c": FailingWitness(),
        },
        threshold=2,
    )

    result = quorum.publish(checkpoint)

    assert result.satisfied is True
    assert result.confirmed_witnesses == (
        "witness-a",
        "witness-b",
    )
    assert result.missing_required_witnesses == ()
    assert "witness-c" in result.failures
    assert len(result.receipts) == 2


def test_three_of_three_fails_when_one_witness_is_unavailable(tmp_path):
    checkpoint = make_checkpoint(tmp_path)
    quorum = WitnessQuorum(
        {
            "witness-a": InMemoryWitnessProvider(
                witness="witness-a",
                key="secret-a",
            ),
            "witness-b": InMemoryWitnessProvider(
                witness="witness-b",
                key="secret-b",
            ),
            "witness-c": FailingWitness(),
        },
        threshold=3,
    )

    result = quorum.publish(checkpoint)

    assert result.satisfied is False
    assert len(result.confirmed_witnesses) == 2
    assert result.failures["witness-c"] == "witness unavailable"


def test_required_witness_must_be_present_even_when_threshold_is_met(tmp_path):
    checkpoint = make_checkpoint(tmp_path)
    quorum = WitnessQuorum(
        {
            "witness-a": InMemoryWitnessProvider(
                witness="witness-a",
                key="secret-a",
            ),
            "witness-b": InMemoryWitnessProvider(
                witness="witness-b",
                key="secret-b",
            ),
            "security-witness": FailingWitness(),
        },
        threshold=2,
        required_witnesses=["security-witness"],
    )

    result = quorum.publish(checkpoint)

    assert result.satisfied is False
    assert result.confirmed_witnesses == (
        "witness-a",
        "witness-b",
    )
    assert result.missing_required_witnesses == (
        "security-witness",
    )


def test_witness_identity_mismatch_does_not_count_toward_quorum(tmp_path):
    checkpoint = make_checkpoint(tmp_path)
    quorum = WitnessQuorum(
        {
            "expected-witness": InMemoryWitnessProvider(
                witness="different-witness",
                key="secret-a",
            ),
        },
        threshold=1,
    )

    result = quorum.publish(checkpoint)

    assert result.satisfied is False
    assert result.confirmed_witnesses == ()
    assert result.failures["expected-witness"].startswith(
        "witness_identity_mismatch:"
    )


def test_duplicate_receipts_from_one_witness_only_count_once(tmp_path):
    checkpoint = make_checkpoint(tmp_path)
    witness_a = InMemoryWitnessProvider(
        witness="witness-a",
        key="secret-a",
    )
    witness_b = InMemoryWitnessProvider(
        witness="witness-b",
        key="secret-b",
    )
    receipt_a = witness_a.publish(checkpoint)

    quorum = WitnessQuorum(
        {
            "witness-a": witness_a,
            "witness-b": witness_b,
        },
        threshold=2,
    )

    result = quorum.evaluate(
        checkpoint,
        [receipt_a, receipt_a],
    )

    assert result.satisfied is False
    assert result.confirmed_witnesses == ("witness-a",)
    assert result.failures["witness-a"] == "duplicate_witness_receipt"


def test_evaluate_rejects_receipt_bound_to_different_checkpoint(tmp_path):
    checkpoint = make_checkpoint(tmp_path)
    witness = InMemoryWitnessProvider(
        witness="witness-a",
        key="secret-a",
    )
    receipt = witness.publish(checkpoint)
    forged = replace(
        receipt,
        checkpoint_head_hash="0" * 64,
    )
    quorum = WitnessQuorum(
        {"witness-a": witness},
        threshold=1,
    )

    result = quorum.evaluate(
        checkpoint,
        [forged],
    )

    assert result.satisfied is False
    assert result.confirmed_witnesses == ()
    assert result.failures["witness-a"] == (
        "checkpoint_head_hash_mismatch"
    )


def test_quorum_rejects_unknown_required_witness():
    try:
        WitnessQuorum(
            {
                "witness-a": InMemoryWitnessProvider(
                    witness="witness-a",
                    key="secret-a",
                )
            },
            threshold=1,
            required_witnesses=["missing-witness"],
        )
    except ValueError as exc:
        assert "not configured" in str(exc)
    else:
        raise AssertionError("unknown required witness accepted")



def request_json(base, path, *, method="GET", body=None):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        base + path,
        method=method,
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_quorum_http_health_transitions_from_unsatisfied_to_satisfied(tmp_path):
    queue = HumanQueue(tmp_path / "queue.db")
    item = queue.ask(
        uri="human://approve",
        title="Quorum HTTP checkpoint",
        source="agent",
    )
    queue.decide(item.id, action="approve", actor="alice")
    signer = AuditCheckpointSigner(
        queue,
        tmp_path / "checkpoints.jsonl",
        key="checkpoint-secret",
    )
    checkpoint = signer.create(now=100)

    quorum = WitnessQuorum(
        {
            "witness-a": InMemoryWitnessProvider(
                witness="witness-a",
                key="secret-a",
            ),
            "witness-b": InMemoryWitnessProvider(
                witness="witness-b",
                key="secret-b",
            ),
            "witness-c": FailingWitness(),
        },
        threshold=2,
    )
    journal = WitnessReceiptJournal(
        tmp_path / "witness-receipts.jsonl"
    )

    httpd = server_module.make_server(
        queue,
        host="127.0.0.1",
        port=0,
        audit_checkpoint_signer=signer,
        audit_witness_receipts=journal,
        audit_witness_quorum=quorum,
    )
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        status, before = request_json(base, "/api/health")
        assert status == 503
        assert before["ok"] is False
        assert before["audit_witness_quorum"]["configured"] is True
        assert before["audit_witness_quorum"]["satisfied"] is False
        assert before["audit_witness_quorum"]["checkpoint_sequence"] == checkpoint.sequence

        status, published = request_json(
            base,
            "/api/audit/checkpoint/witness-quorum",
            method="POST",
            body={"actor": "auditor"},
        )
        assert status == 201
        assert published["quorum"]["satisfied"] is True
        assert published["quorum"]["confirmed_witnesses"] == [
            "witness-a",
            "witness-b",
        ]
        assert "witness-c" in published["quorum"]["failures"]
        assert len(journal.receipts()) == 2

        status, after = request_json(base, "/api/health")
        assert status == 200
        assert after["ok"] is True
        assert after["audit_witness_quorum"]["satisfied"] is True
        assert after["audit_witness_quorum"]["confirmed_witnesses"] == [
            "witness-a",
            "witness-b",
        ]
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_quorum_http_returns_bad_gateway_when_required_witness_missing(tmp_path):
    queue = HumanQueue(tmp_path / "queue.db")
    item = queue.ask(
        uri="human://approve",
        title="Required witness",
        source="agent",
    )
    queue.decide(item.id, action="approve", actor="alice")
    signer = AuditCheckpointSigner(
        queue,
        tmp_path / "checkpoints.jsonl",
        key="checkpoint-secret",
    )
    signer.create(now=100)

    quorum = WitnessQuorum(
        {
            "witness-a": InMemoryWitnessProvider(
                witness="witness-a",
                key="secret-a",
            ),
            "security-witness": FailingWitness(),
        },
        threshold=1,
        required_witnesses=["security-witness"],
    )
    journal = WitnessReceiptJournal(
        tmp_path / "witness-receipts.jsonl"
    )
    httpd = server_module.make_server(
        queue,
        host="127.0.0.1",
        port=0,
        audit_checkpoint_signer=signer,
        audit_witness_receipts=journal,
        audit_witness_quorum=quorum,
    )
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        status, payload = request_json(
            base,
            "/api/audit/checkpoint/witness-quorum",
            method="POST",
            body={"actor": "auditor"},
        )
        assert status == 502
        assert payload["quorum"]["satisfied"] is False
        assert payload["quorum"]["missing_required_witnesses"] == [
            "security-witness"
        ]
        assert len(journal.receipts()) == 1

        status, health = request_json(base, "/api/health")
        assert status == 503
        assert health["audit_witness_quorum"]["satisfied"] is False
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_quorum_health_is_nonfailing_before_first_checkpoint(tmp_path):
    queue = HumanQueue(tmp_path / "queue.db")
    signer = AuditCheckpointSigner(
        queue,
        tmp_path / "checkpoints.jsonl",
        key="checkpoint-secret",
    )
    quorum = WitnessQuorum(
        {
            "witness-a": InMemoryWitnessProvider(
                witness="witness-a",
                key="secret-a",
            )
        },
        threshold=1,
    )
    journal = WitnessReceiptJournal(
        tmp_path / "witness-receipts.jsonl"
    )
    httpd = server_module.make_server(
        queue,
        host="127.0.0.1",
        port=0,
        audit_checkpoint_signer=signer,
        audit_witness_receipts=journal,
        audit_witness_quorum=quorum,
    )
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        status, health = request_json(base, "/api/health")
        assert status == 200
        assert health["ok"] is True
        assert health["audit_witness_quorum"] == {
            "ok": True,
            "configured": True,
            "satisfied": False,
            "checkpoint_sequence": None,
        }
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_quorum_loader_builds_independent_online_witnesses(monkeypatch):
    monkeypatch.setenv(
        "HUMANQUEUE_AUDIT_WITNESS_QUORUM_JSON",
        json.dumps(
            {
                "threshold": 2,
                "required_witnesses": ["witness-a"],
                "witnesses": {
                    "witness-a": {
                        "url": "https://a.example/witness",
                        "verify_url": "https://a.example/verify",
                        "publish_token": "token-a",
                    },
                    "witness-b": {
                        "url": "https://b.example/witness",
                        "verify_url": "https://b.example/verify",
                    },
                },
            }
        ),
    )

    quorum = load_witness_quorum()
    assert quorum is not None
    assert quorum.threshold == 2
    assert quorum.required_witnesses == ("witness-a",)
    assert set(quorum.providers) == {
        "witness-a",
        "witness-b",
    }
    assert (
        quorum.providers["witness-a"].publish_token
        == "token-a"
    )


def test_quorum_loader_rejects_ambiguous_verifier_config(monkeypatch):
    monkeypatch.setenv(
        "HUMANQUEUE_AUDIT_WITNESS_QUORUM_JSON",
        json.dumps(
            {
                "threshold": 1,
                "witnesses": {
                    "witness-a": {
                        "url": "https://a.example/witness",
                        "verify_url": "https://a.example/verify",
                        "keys": {"k1": "shared-secret"},
                    }
                },
            }
        ),
    )

    try:
        load_witness_quorum()
    except ValueError as exc:
        assert "exactly one" in str(exc)
    else:
        raise AssertionError("ambiguous quorum verifier accepted")



def test_quorum_ignores_historical_receipts_for_newer_checkpoint(tmp_path):
    queue = HumanQueue(tmp_path / "queue.db")
    first_wait = queue.ask(
        uri="human://approve",
        title="First checkpoint",
        source="agent",
    )
    queue.decide(first_wait.id, action="approve", actor="alice")
    signer = AuditCheckpointSigner(
        queue,
        tmp_path / "checkpoints.jsonl",
        key="checkpoint-secret",
    )
    checkpoint_one = signer.create(now=100)

    witness_a = InMemoryWitnessProvider(
        witness="witness-a",
        key="secret-a",
    )
    witness_b = InMemoryWitnessProvider(
        witness="witness-b",
        key="secret-b",
    )
    old_receipts = [
        witness_a.publish(checkpoint_one),
        witness_b.publish(checkpoint_one),
    ]

    second_wait = queue.ask(
        uri="human://approve",
        title="Second checkpoint",
        source="agent",
    )
    queue.decide(second_wait.id, action="approve", actor="alice")
    checkpoint_two = signer.create(now=200)
    current_receipts = [
        witness_a.publish(checkpoint_two),
        witness_b.publish(checkpoint_two),
    ]

    quorum = WitnessQuorum(
        {
            "witness-a": witness_a,
            "witness-b": witness_b,
        },
        threshold=2,
    )
    result = quorum.evaluate(
        checkpoint_two,
        old_receipts + current_receipts,
    )

    assert result.satisfied is True
    assert result.confirmed_witnesses == (
        "witness-a",
        "witness-b",
    )
    assert "witness-a" not in result.failures
    assert "witness-b" not in result.failures


def test_quorum_flags_receipt_from_future_checkpoint(tmp_path):
    checkpoint = make_checkpoint(tmp_path)
    witness = InMemoryWitnessProvider(
        witness="witness-a",
        key="secret-a",
    )
    receipt = witness.publish(checkpoint)
    future = replace(
        receipt,
        checkpoint_sequence=checkpoint.sequence + 1,
    )
    quorum = WitnessQuorum(
        {"witness-a": witness},
        threshold=1,
    )

    result = quorum.evaluate(
        checkpoint,
        [future],
    )

    assert result.satisfied is False
    assert result.failures["witness-a"] == "future_checkpoint_receipt"
