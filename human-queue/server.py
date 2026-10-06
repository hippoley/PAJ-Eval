"""Tiny HTTP surface for the HumanQueue runtime.

Run:
    python human-queue/server.py

Then open http://127.0.0.1:8765 and start a producer that uses the same DB.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from runtime import HumanQueue, Wait


ROOT = Path(__file__).resolve().parent
DEFAULT_DB = ROOT / "demo-human-queue.db"
DEFAULT_INDEX = ROOT / "index.html"


def wait_json(item: Wait) -> dict:
    data = asdict(item)
    # Keep the wire contract explicit and JSON-safe.
    return data


def make_handler(queue: HumanQueue, index_path: Path = DEFAULT_INDEX):
    class Handler(BaseHTTPRequestHandler):
        server_version = "HumanQueue/0.1"

        def log_message(self, fmt: str, *args) -> None:
            # Keep the demo readable; errors still return structured JSON.
            return

        def _json(self, status: int, payload: dict | list) -> None:
            body = json.dumps(payload, separators=(",", ":")).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self) -> dict:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                return {}
            raw = self.rfile.read(length)
            try:
                value = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError("invalid JSON") from exc
            if not isinstance(value, dict):
                raise ValueError("JSON body must be an object")
            return value

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path in {"/", "/index.html"}:
                body = index_path.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
                return

            if path == "/api/health":
                self._json(HTTPStatus.OK, {"ok": True, "mode": "durable"})
                return

            if path == "/api/waits":
                self._json(
                    HTTPStatus.OK,
                    {"waits": [wait_json(item) for item in queue.pending()]},
                )
                return

            if path.startswith("/api/waits/"):
                wait_id = path.removeprefix("/api/waits/")
                if not wait_id or "/" in wait_id:
                    self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                    return
                try:
                    item = queue.get(wait_id)
                except KeyError:
                    self._json(HTTPStatus.NOT_FOUND, {"error": "wait_not_found"})
                    return
                self._json(HTTPStatus.OK, {"wait": wait_json(item)})
                return

            self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            try:
                body = self._read_json()
            except ValueError as exc:
                self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return

            if path == "/api/waits":
                required = ("uri", "title", "source")
                missing = [key for key in required if not body.get(key)]
                if missing:
                    self._json(
                        HTTPStatus.BAD_REQUEST,
                        {"error": "missing_fields", "fields": missing},
                    )
                    return
                item = queue.ask(
                    uri=str(body["uri"]),
                    title=str(body["title"]),
                    source=str(body["source"]),
                    payload=body.get("payload") or {},
                    idempotency_key=body.get("idempotency_key"),
                    resume_token=body.get("resume_token"),
                )
                self._json(HTTPStatus.CREATED, {"wait": wait_json(item)})
                return

            suffix = "/decision"
            if path.startswith("/api/waits/") and path.endswith(suffix):
                wait_id = path[len("/api/waits/") : -len(suffix)]
                action = str(body.get("action", "")).strip().lower()
                if not wait_id or not action:
                    self._json(
                        HTTPStatus.BAD_REQUEST,
                        {"error": "wait_id_and_action_required"},
                    )
                    return
                try:
                    item = queue.decide(
                        wait_id,
                        action=action,
                        actor=str(body.get("actor") or "web-human"),
                        value=body.get("value"),
                    )
                except KeyError:
                    self._json(HTTPStatus.NOT_FOUND, {"error": "wait_not_found"})
                    return
                except RuntimeError as exc:
                    self._json(
                        HTTPStatus.CONFLICT,
                        {"error": "decision_conflict", "detail": str(exc)},
                    )
                    return
                self._json(HTTPStatus.OK, {"wait": wait_json(item)})
                return

            self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    return Handler


def make_server(
    queue: HumanQueue,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    index_path: Path = DEFAULT_INDEX,
) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), make_handler(queue, index_path))


def main() -> None:
    db = Path(os.environ.get("HUMANQUEUE_DB", str(DEFAULT_DB)))
    host = os.environ.get("HUMANQUEUE_HOST", "127.0.0.1")
    port = int(os.environ.get("HUMANQUEUE_PORT", "8765"))
    queue = HumanQueue(db)
    server = make_server(queue, host=host, port=port)
    print(f"human:// runtime listening on http://{host}:{port}")
    print(f"queue db: {db}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
