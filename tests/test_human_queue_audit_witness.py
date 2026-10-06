import hashlib
import hmac
import importlib.util
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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


runtime = load("human_queue_runtime_witness", ROOT / "runtime.py")
checkpoint_module = load(
    "human_queue_audit_checkpoint_witness",
    ROOT / "audit_checkpoint.py",
)
witness_module = load(
    "human_queue_audit_witness",
    ROOT / "audit_witness.py",
)
server_module = load("human_queue_server_witness", ROOT / "server.py")

HumanQueue = runtime.HumanQueue
AuditCheckpointSigner = checkpoint_module.AuditCheckpointSigner
WitnessReceipt = witness_module.WitnessReceipt
HmacWitnessReceiptVerifier = witness_module.HmacWitnessReceiptVerifier
HttpCheckpointWitnessProvider = witness_module.HttpCheckpointWitnessProvider
InMemoryWitnessProvider = witness_module.InMemoryWitnessProvider


def make_queue(db):
    queue = HumanQueue(db)
    item = queue.ask(
        uri="human://approve",
        title="Witness checkpoint",
        source="agent",
    )
    queue.decide(item.id, action="approve", actor="alice")
    return queue


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


def sign_receipt(receipt, secret):
    payload = HmacWitnessReceiptVerifier.payload(receipt)
    return hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()


def test_in_memory_witness_returns_independently_signed_receipt(tmp_path):
    queue = make_queue(tmp_path / "queue.db")
    signer = AuditCheckpointSigner(
        queue,
        tmp_path / "checkpoints.jsonl",
        key="checkpoint-secret",
        key_id="checkpoint-key",
    )
    checkpoint = signer.create(now=100)
    witness = InMemoryWitnessProvider(
        witness="control-plane-a",
        key_id="witness-key",
        key="witness-secret",
    )

    receipt = witness.publish(checkpoint)
    assert receipt.checkpoint_sequence == checkpoint.sequence
    assert receipt.checkpoint_signature == checkpoint.signature
    assert receipt.checkpoint_head_hash == checkpoint.head_hash
    assert receipt.key_id == "witness-key"
    assert witness.verify(receipt) is True
    assert "checkpoint-secret" not in json.dumps(asdict(receipt))
    assert "witness-secret" not in json.dumps(asdict(receipt))


def test_http_witness_round_trip_verifies_remote_receipt(tmp_path):
    queue = make_queue(tmp_path / "queue.db")
    signer = AuditCheckpointSigner(
        queue,
        tmp_path / "checkpoints.jsonl",
        key="checkpoint-secret",
    )
    checkpoint = signer.create(now=100)
    witness_secret = "remote-witness-secret"

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            return

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))
            received = payload["checkpoint"]
            assert received["sequence"] == checkpoint.sequence
            assert received["signature"] == checkpoint.signature

            unsigned = WitnessReceipt(
                version=1,
                witness="remote-witness",
                receipt_id="remote-1",
                received_at=200.0,
                checkpoint_sequence=received["sequence"],
                checkpoint_signature=received["signature"],
                checkpoint_head_hash=received["head_hash"],
                key_id="rw1",
                signature="",
            )
            receipt = WitnessReceipt(
                **{
                    **asdict(unsigned),
                    "signature": sign_receipt(unsigned, witness_secret),
                }
            )
            body = json.dumps({"receipt": asdict(receipt)}).encode()
            self.send_response(201)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    endpoint = f"http://127.0.0.1:{httpd.server_address[1]}/witness"

    try:
        provider = HttpCheckpointWitnessProvider(
            endpoint,
            verifier=HmacWitnessReceiptVerifier(
                {"rw1": witness_secret}
            ),
        )
        receipt = provider.publish(checkpoint)
        assert receipt.witness == "remote-witness"
        assert receipt.receipt_id == "remote-1"
        assert provider.verify(receipt) is True
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_http_witness_rejects_receipt_bound_to_wrong_checkpoint(tmp_path):
    queue = make_queue(tmp_path / "queue.db")
    signer = AuditCheckpointSigner(
        queue,
        tmp_path / "checkpoints.jsonl",
        key="checkpoint-secret",
    )
    checkpoint = signer.create(now=100)
    witness_secret = "remote-witness-secret"

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            return

        def do_POST(self):
            unsigned = WitnessReceipt(
                version=1,
                witness="remote-witness",
                receipt_id="bad-1",
                received_at=200.0,
                checkpoint_sequence=checkpoint.sequence + 1,
                checkpoint_signature=checkpoint.signature,
                checkpoint_head_hash=checkpoint.head_hash,
                key_id="rw1",
                signature="",
            )
            receipt = WitnessReceipt(
                **{
                    **asdict(unsigned),
                    "signature": sign_receipt(unsigned, witness_secret),
                }
            )
            body = json.dumps({"receipt": asdict(receipt)}).encode()
            self.send_response(201)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    try:
        provider = HttpCheckpointWitnessProvider(
            f"http://127.0.0.1:{httpd.server_address[1]}/witness",
            verifier=HmacWitnessReceiptVerifier(
                {"rw1": witness_secret}
            ),
        )
        try:
            provider.publish(checkpoint)
        except RuntimeError as exc:
            assert "sequence mismatch" in str(exc)
        else:
            raise AssertionError("mismatched witness receipt accepted")
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_server_publishes_latest_checkpoint_without_creating_another(tmp_path):
    queue = make_queue(tmp_path / "queue.db")
    signer = AuditCheckpointSigner(
        queue,
        tmp_path / "checkpoints.jsonl",
        key="checkpoint-secret",
    )
    checkpoint = signer.create(now=100)
    witness = InMemoryWitnessProvider(
        key="witness-secret",
    )
    httpd = server_module.make_server(
        queue,
        host="127.0.0.1",
        port=0,
        audit_checkpoint_signer=signer,
        audit_witness_provider=witness,
    )
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        status, published = request_json(
            base,
            "/api/audit/checkpoint/witness",
            method="POST",
            body={"actor": "auditor"},
        )
        assert status == 201
        assert published["checkpoint"]["sequence"] == checkpoint.sequence
        assert published["receipt"]["checkpoint_sequence"] == checkpoint.sequence
        assert len(signer.checkpoints()) == 1

        status, published_again = request_json(
            base,
            "/api/audit/checkpoint/witness",
            method="POST",
            body={"actor": "auditor"},
        )
        assert status == 201
        assert published_again["checkpoint"]["sequence"] == checkpoint.sequence
        assert len(signer.checkpoints()) == 1
        assert len(witness.receipts) == 2
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_server_requires_checkpoint_before_witness_publish(tmp_path):
    queue = make_queue(tmp_path / "queue.db")
    signer = AuditCheckpointSigner(
        queue,
        tmp_path / "checkpoints.jsonl",
        key="checkpoint-secret",
    )
    witness = InMemoryWitnessProvider(key="witness-secret")
    httpd = server_module.make_server(
        queue,
        host="127.0.0.1",
        port=0,
        audit_checkpoint_signer=signer,
        audit_witness_provider=witness,
    )
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        status, payload = request_json(
            base,
            "/api/audit/checkpoint/witness",
            method="POST",
            body={"actor": "auditor"},
        )
        assert status == 409
        assert payload["error"] == "audit_checkpoint_missing"
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_server_surfaces_witness_failure_without_creating_checkpoint(tmp_path):
    class FailingWitness:
        def publish(self, checkpoint):
            raise RuntimeError("remote witness unavailable")

        def verify(self, receipt):
            return False

    queue = make_queue(tmp_path / "queue.db")
    signer = AuditCheckpointSigner(
        queue,
        tmp_path / "checkpoints.jsonl",
        key="checkpoint-secret",
    )
    checkpoint = signer.create(now=100)
    httpd = server_module.make_server(
        queue,
        host="127.0.0.1",
        port=0,
        audit_checkpoint_signer=signer,
        audit_witness_provider=FailingWitness(),
    )
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        status, payload = request_json(
            base,
            "/api/audit/checkpoint/witness",
            method="POST",
            body={"actor": "auditor"},
        )
        assert status == 502
        assert payload["error"] == "audit_witness_failed"
        assert payload["checkpoint_sequence"] == checkpoint.sequence
        assert len(signer.checkpoints()) == 1
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()
