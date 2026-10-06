"""Independent audit witness service for HumanQueue.

This service runs in a separate trust domain from the HumanQueue runtime.
It stores the checkpoints it has observed and signs receipts with its own key.
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from audit_checkpoint import AuditCheckpoint
from audit_witness import (
    HmacWitnessReceiptVerifier,
    WitnessReceipt,
    checkpoint_fingerprint,
)


class WitnessStore:
    def __init__(
        self,
        path: str | Path,
        *,
        witness: str,
        key_id: str,
        key: str,
    ) -> None:
        if not witness.strip():
            raise ValueError("witness name is required")
        if not key_id.strip():
            raise ValueError("witness key_id is required")
        if not key:
            raise ValueError("witness signing key is required")
        self.path = Path(path)
        self.witness = witness.strip()
        self.key_id = key_id.strip()
        self.key = key
        self._lock = threading.Lock()
        self.verifier = HmacWitnessReceiptVerifier(
            {self.key_id: self.key}
        )

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
            payload = HmacWitnessReceiptVerifier.payload(unsigned)
            import hashlib
            import hmac

            signature = hmac.new(
                self.key.encode(),
                payload.encode(),
                hashlib.sha256,
            ).hexdigest()
            receipt = WitnessReceipt(
                **{
                    **asdict(unsigned),
                    "signature": signature,
                }
            )

            self.path.parent.mkdir(parents=True, exist_ok=True)
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
            if not self.verifier.verify(receipt):
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


def make_handler(store: WitnessStore):
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
) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(
        (host, port),
        make_handler(store),
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
    )
    server = make_server(
        store,
        host=host,
        port=port,
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
