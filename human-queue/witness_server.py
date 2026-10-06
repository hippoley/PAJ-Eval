"""Independent audit witness service for HumanQueue.

This service runs in a separate trust domain from the HumanQueue runtime.
It stores the checkpoints it has observed and signs receipts with its own key.
"""

from __future__ import annotations

import json
import os
import secrets
import threading
import time
from contextlib import contextmanager
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from audit_checkpoint import AuditCheckpoint
from audit_witness import (
    HmacWitnessReceiptSignatureProvider,
    WitnessReceipt,
    WitnessReceiptSignatureProvider,
    checkpoint_fingerprint,
)


class WitnessStore:
    def __init__(
        self,
        path: str | Path,
        *,
        witness: str,
        key_id: str | None = None,
        key: str | None = None,
        signature_provider: WitnessReceiptSignatureProvider | None = None,
        lock_timeout_seconds: float = 5.0,
        stale_lock_seconds: float = 60.0,
    ) -> None:
        if not witness.strip():
            raise ValueError("witness name is required")
        if signature_provider is not None and (
            key_id is not None or key is not None
        ):
            raise ValueError(
                "custom witness signature_provider cannot be combined with key arguments"
            )
        if signature_provider is None:
            if not (key_id or "").strip():
                raise ValueError("witness key_id is required")
            if not key:
                raise ValueError("witness signing key is required")
            signature_provider = HmacWitnessReceiptSignatureProvider(
                {(key_id or "").strip(): key},
                (key_id or "").strip(),
            )
        if lock_timeout_seconds <= 0:
            raise ValueError("witness lock_timeout_seconds must be > 0")
        if stale_lock_seconds <= 0:
            raise ValueError("witness stale_lock_seconds must be > 0")
        self.path = Path(path)
        self.witness = witness.strip()
        self.signature_provider = signature_provider
        self.key_id = signature_provider.signing_key_id
        self.lock_timeout_seconds = float(lock_timeout_seconds)
        self.stale_lock_seconds = float(stale_lock_seconds)
        self._lock = threading.Lock()

    @property
    def lock_path(self) -> Path:
        return Path(str(self.path) + ".lock")

    @contextmanager
    def _file_lock(self):
        deadline = time.monotonic() + self.lock_timeout_seconds
        self.path.parent.mkdir(parents=True, exist_ok=True)

        while True:
            try:
                fd = os.open(
                    self.lock_path,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    0o600,
                )
                try:
                    os.write(
                        fd,
                        json.dumps(
                            {
                                "pid": os.getpid(),
                                "created_at": time.time(),
                            },
                            sort_keys=True,
                        ).encode(),
                    )
                finally:
                    os.close(fd)
                break
            except FileExistsError:
                try:
                    age = time.time() - self.lock_path.stat().st_mtime
                except FileNotFoundError:
                    continue
                if age > self.stale_lock_seconds:
                    try:
                        self.lock_path.unlink()
                    except FileNotFoundError:
                        pass
                    continue
                if time.monotonic() >= deadline:
                    raise RuntimeError(
                        "timed out waiting for witness store writer lock"
                    )
                time.sleep(0.05)

        try:
            yield
        finally:
            try:
                self.lock_path.unlink()
            except FileNotFoundError:
                pass

    def _records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        records: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    value = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise RuntimeError(
                        f"invalid witness log JSON at line {line_number}"
                    ) from exc
                if not isinstance(value, dict):
                    raise RuntimeError(
                        f"invalid witness log record at line {line_number}"
                    )
                records.append(value)
        return records

    def issue(
        self,
        checkpoint: AuditCheckpoint,
        *,
        received_at: float | None = None,
    ) -> WitnessReceipt:
        fingerprint = checkpoint_fingerprint(checkpoint)
        with self._lock:
            with self._file_lock():
                records = self._records()
                for record in records:
                    if record.get("checkpoint_fingerprint") == fingerprint:
                        receipt = WitnessReceipt(**record["receipt"])
                        if not self.verify(receipt):
                            raise RuntimeError(
                                "stored witness receipt failed verification"
                            )
                        return receipt

                unsigned = WitnessReceipt(
                    version=1,
                    witness=self.witness,
                    receipt_id=f"receipt_{fingerprint[:20]}",
                    received_at=(
                        time.time()
                        if received_at is None
                        else float(received_at)
                    ),
                    checkpoint_sequence=checkpoint.sequence,
                    checkpoint_signature=checkpoint.signature,
                    checkpoint_head_hash=checkpoint.head_hash,
                    key_id=self.key_id,
                    signature="",
                    checkpoint_fingerprint=fingerprint,
                )
                signature = self.signature_provider.sign(unsigned)
                receipt = WitnessReceipt(
                    **{
                        **asdict(unsigned),
                        "signature": signature,
                    }
                )

                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(
                        json.dumps(
                            {
                                "checkpoint_fingerprint": fingerprint,
                                "checkpoint": asdict(checkpoint),
                                "receipt": asdict(receipt),
                            },
                            sort_keys=True,
                            separators=(",", ":"),
                        )
                        + "\n"
                    )
                    handle.flush()
                    os.fsync(handle.fileno())
                return receipt

    def verify(self, receipt: WitnessReceipt) -> bool:
        try:
            if not self.signature_provider.verify(receipt):
                return False
        except KeyError:
            return False

        for record in self._records():
            raw = record.get("receipt")
            if not isinstance(raw, dict):
                continue
            try:
                stored = WitnessReceipt(**raw)
            except TypeError:
                continue
            if stored == receipt:
                return True
        return False

    def count(self) -> int:
        return len(self._records())


def make_handler(
    store: WitnessStore,
    *,
    publish_token: str | None = None,
):
    class Handler(BaseHTTPRequestHandler):
        server_version = "HumanQueueWitness/0.1"

        def log_message(self, fmt: str, *args) -> None:
            return

        def _json(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            try:
                value = json.loads(raw or b"{}")
            except json.JSONDecodeError as exc:
                raise ValueError("invalid_json") from exc
            if not isinstance(value, dict):
                raise ValueError("json_object_required")
            return value

        def do_GET(self) -> None:
            if self.path == "/health":
                self._json(
                    HTTPStatus.OK,
                    {
                        "ok": True,
                        "witness": store.witness,
                        "records": store.count(),
                    },
                )
                return
            self._json(
                HTTPStatus.NOT_FOUND,
                {"error": "not_found"},
            )

        def do_POST(self) -> None:
            try:
                body = self._read_json()
            except ValueError as exc:
                self._json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": str(exc)},
                )
                return

            if self.path == "/witness":
                if publish_token is not None:
                    authorization = self.headers.get("Authorization", "")
                    expected = f"Bearer {publish_token}"
                    if not secrets.compare_digest(
                        authorization,
                        expected,
                    ):
                        self._json(
                            HTTPStatus.UNAUTHORIZED,
                            {"error": "witness_publish_authentication_required"},
                        )
                        return
                raw_checkpoint = body.get("checkpoint")
                supplied_fingerprint = body.get(
                    "checkpoint_fingerprint"
                )
                if not isinstance(raw_checkpoint, dict):
                    self._json(
                        HTTPStatus.BAD_REQUEST,
                        {"error": "checkpoint_required"},
                    )
                    return
                try:
                    checkpoint = AuditCheckpoint(**raw_checkpoint)
                except TypeError as exc:
                    self._json(
                        HTTPStatus.BAD_REQUEST,
                        {
                            "error": "invalid_checkpoint",
                            "detail": str(exc),
                        },
                    )
                    return
                fingerprint = checkpoint_fingerprint(checkpoint)
                if supplied_fingerprint != fingerprint:
                    self._json(
                        HTTPStatus.BAD_REQUEST,
                        {"error": "checkpoint_fingerprint_mismatch"},
                    )
                    return
                try:
                    receipt = store.issue(checkpoint)
                except RuntimeError as exc:
                    self._json(
                        HTTPStatus.CONFLICT,
                        {
                            "error": "witness_store_conflict",
                            "detail": str(exc),
                        },
                    )
                    return
                self._json(
                    HTTPStatus.CREATED,
                    {"receipt": asdict(receipt)},
                )
                return

            if self.path == "/verify":
                raw_receipt = body.get("receipt")
                if not isinstance(raw_receipt, dict):
                    self._json(
                        HTTPStatus.BAD_REQUEST,
                        {"error": "receipt_required"},
                    )
                    return
                try:
                    receipt = WitnessReceipt(**raw_receipt)
                except TypeError as exc:
                    self._json(
                        HTTPStatus.BAD_REQUEST,
                        {
                            "error": "invalid_receipt",
                            "detail": str(exc),
                        },
                    )
                    return
                self._json(
                    HTTPStatus.OK,
                    {"valid": store.verify(receipt)},
                )
                return

            self._json(
                HTTPStatus.NOT_FOUND,
                {"error": "not_found"},
            )

    return Handler


def make_server(
    store: WitnessStore,
    *,
    host: str = "127.0.0.1",
    port: int = 8876,
    publish_token: str | None = None,
) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(
        (host, port),
        make_handler(
            store,
            publish_token=publish_token,
        ),
    )


def main() -> None:
    root = Path(__file__).resolve().parent
    host = os.environ.get(
        "HUMANQUEUE_WITNESS_HOST",
        "127.0.0.1",
    )
    port = int(
        os.environ.get(
            "HUMANQUEUE_WITNESS_PORT",
            "8876",
        )
    )
    log_path = os.environ.get(
        "HUMANQUEUE_WITNESS_LOG",
        str(root / "demo-witness.jsonl"),
    )
    witness = os.environ.get(
        "HUMANQUEUE_WITNESS_NAME",
        "humanqueue-witness",
    )
    key_id = os.environ.get(
        "HUMANQUEUE_WITNESS_KEY_ID",
        "w1",
    )
    key = os.environ.get(
        "HUMANQUEUE_WITNESS_KEY",
        "",
    )
    if not key:
        raise SystemExit(
            "HUMANQUEUE_WITNESS_KEY is required"
        )

    store = WitnessStore(
        log_path,
        witness=witness,
        key_id=key_id,
        key=key,
        lock_timeout_seconds=float(
            os.environ.get(
                "HUMANQUEUE_WITNESS_LOCK_TIMEOUT_SECONDS",
                "5",
            )
        ),
        stale_lock_seconds=float(
            os.environ.get(
                "HUMANQUEUE_WITNESS_STALE_LOCK_SECONDS",
                "60",
            )
        ),
    )
    server = make_server(
        store,
        host=host,
        port=port,
        publish_token=os.environ.get(
            "HUMANQUEUE_WITNESS_PUBLISH_TOKEN",
            "",
        ) or None,
    )
    print(
        f"human:// witness listening on http://{host}:{port}"
    )
    print(f"witness log: {log_path}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down witness")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
