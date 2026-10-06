"""Tiny HTTP surface for the HumanQueue runtime.

Run:
    python human-queue/server.py

Then open http://127.0.0.1:8765 and start a producer that uses the same DB.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from adapters import RetryPolicy
from delivery import DurableDeliveryQueue, Delivery
from destinations import DestinationRegistry, ResumeDestination, resolve_resume_binding
from runtime import HumanQueue, Wait


ROOT = Path(__file__).resolve().parent
DEFAULT_DB = ROOT / "demo-human-queue.db"
DEFAULT_INDEX = ROOT / "index.html"


def wait_json(item: Wait) -> dict:
    data = asdict(item)
    # Keep the wire contract explicit and JSON-safe.
    return data


def delivery_json(item: Delivery) -> dict:
    return asdict(item)


def destination_json(item: ResumeDestination) -> dict:
    return {
        "name": item.name,
        "adapter": item.adapter,
        "target": item.target,
        "policy": asdict(item.policy),
        "enabled": item.enabled,
        "revision": item.revision,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def _binding_policy(binding: dict) -> RetryPolicy:
    return RetryPolicy(
        max_attempts=int(binding.get("max_attempts") or 3),
        base_delay=float(binding.get("base_delay") or 0.25),
        multiplier=float(binding.get("multiplier") or 2.0),
        max_delay=float(binding.get("max_delay") or 5.0),
    )


def make_handler(
    queue: HumanQueue,
    index_path: Path = DEFAULT_INDEX,
    deliveries: DurableDeliveryQueue | None = None,
    destinations: DestinationRegistry | None = None,
):
    deliveries = deliveries or DurableDeliveryQueue(queue.db_path)
    destinations = destinations or DestinationRegistry(queue.db_path)
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

            if path == "/api/events":
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-cache, no-transform")
                self.send_header("Connection", "keep-alive")
                self.end_headers()
                last_signature = None
                heartbeat_at = 0.0
                try:
                    while True:
                        waits = [wait_json(item) for item in queue.pending()]
                        events = [
                            asdict(event)
                            for event in queue.recent_audit_events(limit=50)
                        ]
                        signature = json.dumps(
                            {
                                "waits": waits,
                                "last_event_id": events[-1]["id"] if events else None,
                            },
                            sort_keys=True,
                            separators=(",", ":"),
                        )
                        now = time.monotonic()
                        if signature != last_signature:
                            payload = json.dumps(
                                {"waits": waits, "events": events},
                                separators=(",", ":"),
                            )
                            frame = f"event: queue\ndata: {payload}\n\n".encode()
                            self.wfile.write(frame)
                            self.wfile.flush()
                            last_signature = signature
                            heartbeat_at = now
                        elif now - heartbeat_at >= 10:
                            self.wfile.write(b": heartbeat\n\n")
                            self.wfile.flush()
                            heartbeat_at = now
                        time.sleep(0.15)
                except (BrokenPipeError, ConnectionResetError):
                    return

            if path == "/api/waits":
                self._json(
                    HTTPStatus.OK,
                    {"waits": [wait_json(item) for item in queue.pending()]},
                )
                return

            if path == "/api/destinations":
                self._json(
                    HTTPStatus.OK,
                    {
                        "destinations": [
                            destination_json(item)
                            for item in destinations.list()
                        ]
                    },
                )
                return

            if path.startswith("/api/destinations/") and path.endswith("/history"):
                name = path[len("/api/destinations/") : -len("/history")]
                if not name or "/" in name:
                    self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                    return
                self._json(
                    HTTPStatus.OK,
                    {
                        "history": [
                            destination_json(item)
                            for item in destinations.history(name)
                        ]
                    },
                )
                return

            if path == "/api/deliveries":
                self._json(
                    HTTPStatus.OK,
                    {
                        "deliveries": [
                            delivery_json(item)
                            for item in deliveries.list(limit=100)
                        ]
                    },
                )
                return

            if path == "/api/audit":
                self._json(
                    HTTPStatus.OK,
                    {
                        "events": [
                            asdict(event)
                            for event in queue.recent_audit_events(limit=100)
                        ]
                    },
                )
                return

            if path.startswith("/api/waits/") and path.endswith("/events"):
                wait_id = path[len("/api/waits/") : -len("/events")]
                if not wait_id or "/" in wait_id:
                    self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                    return
                try:
                    events = queue.audit_events(wait_id)
                except KeyError:
                    self._json(HTTPStatus.NOT_FOUND, {"error": "wait_not_found"})
                    return
                self._json(
                    HTTPStatus.OK,
                    {"events": [asdict(event) for event in events]},
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

            if path == "/api/destinations":
                name = str(body.get("name") or "").strip()
                adapter_name = str(body.get("adapter") or "").strip()
                target = str(body.get("target") or "").strip()
                if not name or not adapter_name or not target:
                    self._json(
                        HTTPStatus.BAD_REQUEST,
                        {"error": "name_adapter_and_target_required"},
                    )
                    return
                try:
                    policy = RetryPolicy(
                        max_attempts=int(body.get("max_attempts") or 3),
                        base_delay=float(body.get("base_delay") or 0.25),
                        multiplier=float(body.get("multiplier") or 2.0),
                        max_delay=float(body.get("max_delay") or 5.0),
                    )
                    item = destinations.put(
                        name,
                        adapter=adapter_name,
                        target=target,
                        policy=policy,
                        enabled=bool(body.get("enabled", True)),
                    )
                except (TypeError, ValueError) as exc:
                    self._json(
                        HTTPStatus.BAD_REQUEST,
                        {"error": "invalid_destination", "detail": str(exc)},
                    )
                    return
                self._json(
                    HTTPStatus.CREATED,
                    {"destination": destination_json(item)},
                )
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
                binding = body.get("resume_binding")
                if binding is not None:
                    if not isinstance(binding, dict):
                        self._json(
                            HTTPStatus.BAD_REQUEST,
                            {
                                "error": "invalid_resume_binding",
                                "detail": "resume_binding must be an object",
                            },
                        )
                        return
                    try:
                        resolve_resume_binding(binding, destinations)
                    except (KeyError, RuntimeError, TypeError, ValueError) as exc:
                        self._json(
                            HTTPStatus.BAD_REQUEST,
                            {"error": "invalid_resume_binding", "detail": str(exc)},
                        )
                        return

                item = queue.ask(
                    uri=str(body["uri"]),
                    title=str(body["title"]),
                    source=str(body["source"]),
                    payload=body.get("payload") or {},
                    idempotency_key=body.get("idempotency_key"),
                    resume_token=body.get("resume_token"),
                    resume_binding=binding,
                )
                self._json(HTTPStatus.CREATED, {"wait": wait_json(item)})
                return

            delivery_suffix = "/delivery"
            if path.startswith("/api/waits/") and path.endswith(delivery_suffix):
                wait_id = path[len("/api/waits/") : -len(delivery_suffix)]
                adapter_name = str(body.get("adapter") or "").strip()
                target = str(body.get("target") or "").strip()
                if not wait_id or not adapter_name or not target:
                    self._json(
                        HTTPStatus.BAD_REQUEST,
                        {"error": "wait_id_adapter_and_target_required"},
                    )
                    return
                try:
                    item = queue.get(wait_id)
                except KeyError:
                    self._json(HTTPStatus.NOT_FOUND, {"error": "wait_not_found"})
                    return
                if item.execution_state not in {
                    "resume_requested",
                    "resumed",
                    "completed",
                    "failed",
                }:
                    self._json(
                        HTTPStatus.CONFLICT,
                        {"error": "wait_has_no_resume_request"},
                    )
                    return
                try:
                    policy = RetryPolicy(
                        max_attempts=int(body.get("max_attempts") or 3),
                        base_delay=float(body.get("base_delay") or 0.25),
                        multiplier=float(body.get("multiplier") or 2.0),
                        max_delay=float(body.get("max_delay") or 5.0),
                    )
                    job = deliveries.enqueue(
                        wait_id,
                        adapter=adapter_name,
                        target=target,
                        policy=policy,
                    )
                except (TypeError, ValueError) as exc:
                    self._json(
                        HTTPStatus.BAD_REQUEST,
                        {"error": "invalid_delivery_policy", "detail": str(exc)},
                    )
                    return
                self._json(
                    HTTPStatus.CREATED,
                    {"delivery": delivery_json(job)},
                )
                return

            resumed_suffix = "/resumed"
            if path.startswith("/api/waits/") and path.endswith(resumed_suffix):
                wait_id = path[len("/api/waits/") : -len(resumed_suffix)]
                actor = str(body.get("actor") or "machine")
                try:
                    item = queue.mark_resumed(wait_id, actor=actor)
                except KeyError:
                    self._json(HTTPStatus.NOT_FOUND, {"error": "wait_not_found"})
                    return
                except RuntimeError as exc:
                    self._json(
                        HTTPStatus.CONFLICT,
                        {"error": "resume_conflict", "detail": str(exc)},
                    )
                    return
                self._json(HTTPStatus.OK, {"wait": wait_json(item)})
                return

            complete_suffix = "/complete"
            if path.startswith("/api/waits/") and path.endswith(complete_suffix):
                wait_id = path[len("/api/waits/") : -len(complete_suffix)]
                actor = str(body.get("actor") or "machine")
                success = bool(body.get("success", True))
                try:
                    item = queue.mark_completed(
                        wait_id,
                        actor=actor,
                        success=success,
                        detail=body.get("detail"),
                    )
                except KeyError:
                    self._json(HTTPStatus.NOT_FOUND, {"error": "wait_not_found"})
                    return
                except RuntimeError as exc:
                    self._json(
                        HTTPStatus.CONFLICT,
                        {"error": "completion_conflict", "detail": str(exc)},
                    )
                    return
                self._json(HTTPStatus.OK, {"wait": wait_json(item)})
                return

            claim_suffix = "/claim"
            if path.startswith("/api/waits/") and path.endswith(claim_suffix):
                wait_id = path[len("/api/waits/") : -len(claim_suffix)]
                actor = str(body.get("actor") or "").strip()
                if not wait_id or not actor:
                    self._json(
                        HTTPStatus.BAD_REQUEST,
                        {"error": "wait_id_and_actor_required"},
                    )
                    return
                try:
                    item = queue.claim(
                        wait_id,
                        actor=actor,
                        lease_seconds=float(body.get("lease_seconds") or 30),
                    )
                except KeyError:
                    self._json(HTTPStatus.NOT_FOUND, {"error": "wait_not_found"})
                    return
                except (RuntimeError, ValueError) as exc:
                    self._json(
                        HTTPStatus.CONFLICT,
                        {"error": "claim_conflict", "detail": str(exc)},
                    )
                    return
                self._json(HTTPStatus.OK, {"wait": wait_json(item)})
                return

            release_suffix = "/release"
            if path.startswith("/api/waits/") and path.endswith(release_suffix):
                wait_id = path[len("/api/waits/") : -len(release_suffix)]
                actor = str(body.get("actor") or "").strip()
                if not wait_id or not actor:
                    self._json(
                        HTTPStatus.BAD_REQUEST,
                        {"error": "wait_id_and_actor_required"},
                    )
                    return
                try:
                    item = queue.release_claim(wait_id, actor=actor)
                except KeyError:
                    self._json(HTTPStatus.NOT_FOUND, {"error": "wait_not_found"})
                    return
                except RuntimeError as exc:
                    self._json(
                        HTTPStatus.CONFLICT,
                        {"error": "claim_conflict", "detail": str(exc)},
                    )
                    return
                self._json(HTTPStatus.OK, {"wait": wait_json(item)})
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
                resolved = None
                if action != "reject":
                    try:
                        current = queue.get(wait_id)
                    except KeyError:
                        self._json(HTTPStatus.NOT_FOUND, {"error": "wait_not_found"})
                        return
                    if current.resume_binding:
                        try:
                            resolved = resolve_resume_binding(
                                current.resume_binding,
                                destinations,
                            )
                        except (KeyError, RuntimeError, TypeError, ValueError) as exc:
                            self._json(
                                HTTPStatus.CONFLICT,
                                {
                                    "error": "resume_destination_unavailable",
                                    "detail": str(exc),
                                },
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
                response = {"wait": wait_json(item)}
                if item.execution_state == "resume_requested" and resolved:
                    adapter_name = str(resolved["adapter"]).strip()
                    target = str(resolved["target"]).strip()
                    try:
                        job = deliveries.enqueue(
                            item.id,
                            adapter=adapter_name,
                            target=target,
                            policy=_binding_policy(resolved),
                            destination=resolved.get("destination"),
                            destination_revision=resolved.get("destination_revision"),
                        )
                    except (TypeError, ValueError) as exc:
                        self._json(
                            HTTPStatus.CONFLICT,
                            {"error": "invalid_resume_binding", "detail": str(exc)},
                        )
                        return
                    queue.mark_resume_delivery_queued(
                        item.id,
                        actor="runtime",
                        adapter=adapter_name,
                        target=target,
                        delivery_id=job.id,
                        destination=resolved.get("destination"),
                        destination_revision=resolved.get("destination_revision"),
                    )
                    response["delivery"] = delivery_json(job)
                self._json(HTTPStatus.OK, response)
                return

            self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    return Handler


def make_server(
    queue: HumanQueue,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    index_path: Path = DEFAULT_INDEX,
    deliveries: DurableDeliveryQueue | None = None,
    destinations: DestinationRegistry | None = None,
) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(
        (host, port),
        make_handler(queue, index_path, deliveries, destinations),
    )


def main() -> None:
    db = Path(os.environ.get("HUMANQUEUE_DB", str(DEFAULT_DB)))
    host = os.environ.get("HUMANQUEUE_HOST", "127.0.0.1")
    port = int(os.environ.get("HUMANQUEUE_PORT", "8765"))
    queue = HumanQueue(db)
    deliveries = DurableDeliveryQueue(db)
    destinations = DestinationRegistry(db)
    server = make_server(
        queue,
        host=host,
        port=port,
        deliveries=deliveries,
        destinations=destinations,
    )
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
