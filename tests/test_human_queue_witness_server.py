import hashlib
import hmac
import importlib.util
import json
import sys
import threading
import urllib.error
import urllib.request
from dataclasses import asdict
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


runtime = load("human_queue_runtime_witness_server", ROOT / "runtime.py")
checkpoint_module = load(
    "human_queue_checkpoint_witness_server",
    ROOT / "audit_checkpoint.py",
)
witness_module = load(
    "human_queue_witness_client_server_test",
    ROOT / "audit_witness.py",
)
witness_server = load(
    "human_queue_witness_server",
    ROOT / "witness_server.py",
)

HumanQueue = runtime.HumanQueue
AuditCheckpointSigner = checkpoint_module.AuditCheckpointSigner
WitnessReceipt = witness_module.WitnessReceipt
OnlineWitnessReceiptVerifier = witness_module.OnlineWitnessReceiptVerifier
HttpCheckpointWitnessProvider = witness_module.HttpCheckpointWitnessProvider
HmacWitnessReceiptVerifier = witness_module.HmacWitnessReceiptVerifier
checkpoint_fingerprint = witness_module.checkpoint_fingerprint
WitnessStore = witness_server.WitnessStore


def make_checkpoint(tmp_path):
    queue = HumanQueue(tmp_path / "queue.db")
    item = queue.ask(
        uri="human://approve",
        title="Witness server proof",
        source="agent",
    )
    queue.decide(item.id, action="approve", actor="alice")
    signer = AuditCheckpointSigner(
        queue,
        tmp_path / "checkpoints.jsonl",
        key="checkpoint-secret",
    )
    return signer.create(now=100)


def post_json(base, path, payload, *, headers=None):
    request = urllib.request.Request(
        base + path,
        method="POST",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_witness_store_is_idempotent_for_same_checkpoint(tmp_path):
    checkpoint = make_checkpoint(tmp_path)
    store = WitnessStore(
        tmp_path / "witness.jsonl",
        witness="witness-a",
        key_id="w1",
        key="witness-secret",
    )

    first = store.issue(checkpoint, received_at=200)
    second = store.issue(checkpoint, received_at=300)

    assert first == second
    assert first.received_at == 200
    assert first.checkpoint_fingerprint == checkpoint_fingerprint(checkpoint)
    assert store.count() == 1
    assert store.verify(first) is True


def test_witness_store_restart_verifies_existing_receipt(tmp_path):
    checkpoint = make_checkpoint(tmp_path)
    path = tmp_path / "witness.jsonl"
    first_store = WitnessStore(
        path,
        witness="witness-a",
        key_id="w1",
        key="witness-secret",
    )
    receipt = first_store.issue(checkpoint, received_at=200)

    reopened = WitnessStore(
        path,
        witness="witness-a",
        key_id="w1",
        key="witness-secret",
    )
    assert reopened.count() == 1
    assert reopened.verify(receipt) is True
    assert reopened.issue(checkpoint, received_at=999) == receipt


def test_online_client_round_trips_against_independent_witness_server(tmp_path):
    checkpoint = make_checkpoint(tmp_path)
    store = WitnessStore(
        tmp_path / "witness.jsonl",
        witness="witness-a",
        key_id="w1",
        key="witness-secret",
    )
    httpd = witness_server.make_server(
        store,
        host="127.0.0.1",
        port=0,
    )
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        provider = HttpCheckpointWitnessProvider(
            base + "/witness",
            verifier=OnlineWitnessReceiptVerifier(
                base + "/verify"
            ),
        )
        receipt = provider.publish(checkpoint)
        assert receipt.witness == "witness-a"
        assert receipt.checkpoint_fingerprint == checkpoint_fingerprint(
            checkpoint
        )
        assert provider.verify(receipt) is True
        assert store.count() == 1

        replay = provider.publish(checkpoint)
        assert replay == receipt
        assert store.count() == 1

        status, health = post_json(
            base,
            "/verify",
            {"receipt": asdict(receipt)},
        )
        assert status == 200
        assert health == {"valid": True}
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_witness_verify_rejects_valid_hmac_receipt_not_in_store(tmp_path):
    checkpoint = make_checkpoint(tmp_path)
    store = WitnessStore(
        tmp_path / "witness.jsonl",
        witness="witness-a",
        key_id="w1",
        key="witness-secret",
    )
    real = store.issue(checkpoint, received_at=200)

    unsigned = WitnessReceipt(
        version=1,
        witness="witness-a",
        receipt_id="receipt_not_recorded",
        received_at=201,
        checkpoint_sequence=checkpoint.sequence,
        checkpoint_signature=checkpoint.signature,
        checkpoint_head_hash=checkpoint.head_hash,
        key_id="w1",
        signature="",
        checkpoint_fingerprint=checkpoint_fingerprint(checkpoint),
    )
    payload = HmacWitnessReceiptVerifier.payload(unsigned)
    forged = WitnessReceipt(
        **{
            **asdict(unsigned),
            "signature": hmac.new(
                b"witness-secret",
                payload.encode(),
                hashlib.sha256,
            ).hexdigest(),
        }
    )

    assert forged.signature != real.signature
    assert store.verifier.verify(forged) is True
    assert store.verify(forged) is False


def test_witness_server_rejects_checkpoint_fingerprint_mismatch(tmp_path):
    checkpoint = make_checkpoint(tmp_path)
    store = WitnessStore(
        tmp_path / "witness.jsonl",
        witness="witness-a",
        key_id="w1",
        key="witness-secret",
    )
    httpd = witness_server.make_server(
        store,
        host="127.0.0.1",
        port=0,
    )
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        status, payload = post_json(
            base,
            "/witness",
            {
                "checkpoint": asdict(checkpoint),
                "checkpoint_fingerprint": "0" * 64,
            },
        )
        assert status == 400
        assert payload["error"] == "checkpoint_fingerprint_mismatch"
        assert store.count() == 0
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_witness_publish_endpoint_can_require_bearer_auth(tmp_path):
    checkpoint = make_checkpoint(tmp_path)
    store = WitnessStore(
        tmp_path / "witness.jsonl",
        witness="witness-a",
        key_id="w1",
        key="witness-secret",
    )
    httpd = witness_server.make_server(
        store,
        host="127.0.0.1",
        port=0,
        publish_token="publish-token",
    )
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        payload = {
            "checkpoint": asdict(checkpoint),
            "checkpoint_fingerprint": checkpoint_fingerprint(checkpoint),
        }
        status, denied = post_json(
            base,
            "/witness",
            payload,
        )
        assert status == 401
        assert denied["error"] == "witness_publish_authentication_required"

        status, denied = post_json(
            base,
            "/witness",
            payload,
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert status == 401
        assert denied["error"] == "witness_publish_authentication_required"
        assert store.count() == 0

        provider = HttpCheckpointWitnessProvider(
            base + "/witness",
            verifier=OnlineWitnessReceiptVerifier(
                base + "/verify"
            ),
            publish_token="publish-token",
        )
        receipt = provider.publish(checkpoint)
        assert receipt.checkpoint_sequence == checkpoint.sequence
        assert store.count() == 1

        status, verified = post_json(
            base,
            "/verify",
            {"receipt": asdict(receipt)},
        )
        assert status == 200
        assert verified == {"valid": True}
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()
