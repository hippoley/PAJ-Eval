import importlib.util
import json
import sys
import threading
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


ROOT = Path(__file__).parents[1] / "human-queue"
sys.path.insert(0, str(ROOT))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


runtime = load("runtime", ROOT / "runtime.py")
server_module = load("human_queue_server", ROOT / "server.py")
HumanQueue = runtime.HumanQueue


def request_json(base, path, *, method="GET", body=None, headers=None):
    data = None if body is None else json.dumps(body).encode()
    request = Request(
        base + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        with urlopen(request, timeout=2) as response:
            return response.status, json.loads(response.read())
    except HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_http_wait_decision_resume_contract(tmp_path):
    queue = HumanQueue(tmp_path / "queue.db")
    httpd = server_module.make_server(queue, host="127.0.0.1", port=0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        status, health = request_json(base, "/api/health")
        assert status == 200
        assert health == {"ok": True, "mode": "durable"}

        status, created = request_json(
            base,
            "/api/waits",
            method="POST",
            body={
                "uri": "human://approve",
                "title": "Ship release?",
                "source": "ci",
                "idempotency_key": "release-7",
                "resume_token": "deploy-step",
                "payload": {"priority": 99, "actions": ["Approve", "Reject"]},
            },
        )
        assert status == 201
        wait_id = created["wait"]["id"]

        status, pending = request_json(base, "/api/waits")
        assert status == 200
        assert [item["id"] for item in pending["waits"]] == [wait_id]

        status, decided = request_json(
            base,
            f"/api/waits/{wait_id}/decision",
            method="POST",
            body={"action": "approve", "actor": "web-human"},
        )
        assert status == 200
        assert decided["wait"]["state"] == "approved"
        assert decided["wait"]["resume_token"] == "deploy-step"

        status, pending = request_json(base, "/api/waits")
        assert status == 200
        assert pending == {"waits": []}
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_http_rejects_conflicting_second_decision(tmp_path):
    queue = HumanQueue(tmp_path / "queue.db")
    item = queue.ask(uri="human://approve", title="Delete?", source="agent")
    httpd = server_module.make_server(queue, host="127.0.0.1", port=0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        status, _ = request_json(
            base,
            f"/api/waits/{item.id}/decision",
            method="POST",
            body={"action": "approve", "actor": "web-human"},
        )
        assert status == 200

        status, conflict = request_json(
            base,
            f"/api/waits/{item.id}/decision",
            method="POST",
            body={"action": "reject", "actor": "web-human"},
        )
        assert status == 409
        assert conflict["error"] == "decision_conflict"
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_http_validates_required_wait_fields(tmp_path):
    queue = HumanQueue(tmp_path / "queue.db")
    httpd = server_module.make_server(queue, host="127.0.0.1", port=0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        status, payload = request_json(
            base,
            "/api/waits",
            method="POST",
            body={"title": "Missing source and uri"},
        )
        assert status == 400
        assert payload["error"] == "missing_fields"
        assert set(payload["fields"]) == {"uri", "source"}
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_sse_stream_emits_queue_snapshot_and_change(tmp_path):
    queue = HumanQueue(tmp_path / "queue.db")
    httpd = server_module.make_server(queue, host="127.0.0.1", port=0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        request = Request(base + "/api/events", method="GET")
        with urlopen(request, timeout=2) as response:
            assert response.status == 200
            assert response.headers["Content-Type"].startswith("text/event-stream")

            event = response.readline().decode().strip()
            data = response.readline().decode().strip()
            blank = response.readline().decode().strip()
            assert event == "event: queue"
            assert data.startswith("data: ")
            assert blank == ""
            assert json.loads(data.removeprefix("data: ")) == {"waits": [], "events": []}

            queue.ask(
                uri="human://approve",
                title="Live task?",
                source="agent",
                idempotency_key="sse-task",
            )

            event = response.readline().decode().strip()
            data = response.readline().decode().strip()
            blank = response.readline().decode().strip()
            assert event == "event: queue"
            payload = json.loads(data.removeprefix("data: "))
            assert blank == ""
            assert len(payload["waits"]) == 1
            assert payload["waits"][0]["title"] == "Live task?"
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_http_exposes_audit_provenance(tmp_path):
    queue = HumanQueue(tmp_path / "queue.db")
    item = queue.ask(uri="human://approve", title="Trace?", source="agent")
    queue.claim(item.id, actor="alice", lease_seconds=1)
    queue.decide(item.id, action="approve", actor="alice")

    httpd = server_module.make_server(queue, host="127.0.0.1", port=0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        status, one = request_json(base, f"/api/waits/{item.id}/events")
        assert status == 200
        assert [e["event_type"] for e in one["events"]] == [
            "WAIT_CREATED",
            "CLAIMED",
            "DECISION_COMMITTED",
            "RESUME_REQUESTED",
        ]

        status, recent = request_json(base, "/api/audit")
        assert status == 200
        assert recent["events"][-1]["event_type"] == "RESUME_REQUESTED"
        assert recent["events"][-1]["actor"] == "alice"
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_http_machine_acknowledgement_protocol(tmp_path):
    queue = HumanQueue(tmp_path / "queue.db")
    item = queue.ask(
        uri="human://approve",
        title="Run step?",
        source="agent",
        resume_token="step-http",
    )
    queue.decide(item.id, action="approve", actor="alice")

    httpd = server_module.make_server(queue, host="127.0.0.1", port=0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        status, resumed = request_json(
            base,
            f"/api/waits/{item.id}/resumed",
            method="POST",
            body={"actor": "agent"},
        )
        assert status == 200
        assert resumed["wait"]["execution_state"] == "resumed"

        status, completed = request_json(
            base,
            f"/api/waits/{item.id}/complete",
            method="POST",
            body={"actor": "agent", "success": True, "detail": "done"},
        )
        assert status == 200
        assert completed["wait"]["execution_state"] == "completed"

        status, events = request_json(base, f"/api/waits/{item.id}/events")
        assert status == 200
        assert [event["event_type"] for event in events["events"]][-3:] == [
            "RESUME_REQUESTED",
            "PROCESS_RESUMED",
            "PROCESS_COMPLETED",
        ]
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_http_enqueues_and_lists_durable_delivery(tmp_path):
    queue = HumanQueue(tmp_path / "queue.db")
    item = queue.ask(
        uri="human://approve",
        title="Resume through worker?",
        source="agent",
        resume_token="worker-step",
    )
    queue.decide(item.id, action="approve", actor="alice")

    httpd = server_module.make_server(queue, host="127.0.0.1", port=0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        status, created = request_json(
            base,
            f"/api/waits/{item.id}/delivery",
            method="POST",
            body={
                "adapter": "webhook",
                "target": "https://worker.example/resume",
                "max_attempts": 4,
                "base_delay": 1,
                "multiplier": 2,
                "max_delay": 8,
            },
        )
        assert status == 201
        job = created["delivery"]
        assert job["wait_id"] == item.id
        assert job["status"] == "pending"
        assert job["attempt"] == 0
        assert job["max_attempts"] == 4

        status, listing = request_json(base, "/api/deliveries")
        assert status == 200
        assert len(listing["deliveries"]) == 1
        assert listing["deliveries"][0]["id"] == job["id"]

        status, duplicate = request_json(
            base,
            f"/api/waits/{item.id}/delivery",
            method="POST",
            body={
                "adapter": "webhook",
                "target": "https://worker.example/resume",
            },
        )
        assert status == 201
        assert duplicate["delivery"]["id"] == job["id"]
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_http_refuses_delivery_before_human_decision(tmp_path):
    queue = HumanQueue(tmp_path / "queue.db")
    item = queue.ask(
        uri="human://approve",
        title="Not yet",
        source="agent",
    )
    httpd = server_module.make_server(queue, host="127.0.0.1", port=0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        status, payload = request_json(
            base,
            f"/api/waits/{item.id}/delivery",
            method="POST",
            body={"adapter": "webhook", "target": "https://worker.example/resume"},
        )
        assert status == 409
        assert payload["error"] == "wait_has_no_resume_request"
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_resume_binding_auto_materializes_delivery_on_approve(tmp_path):
    queue = HumanQueue(tmp_path / "queue.db")
    httpd = server_module.make_server(queue, host="127.0.0.1", port=0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        status, created = request_json(
            base,
            "/api/waits",
            method="POST",
            body={
                "uri": "human://approve",
                "title": "Auto resume?",
                "source": "agent",
                "resume_token": "step-auto",
                "resume_binding": {
                    "adapter": "webhook",
                    "target": "https://worker.example/resume",
                    "max_attempts": 4,
                    "base_delay": 1,
                    "multiplier": 2,
                    "max_delay": 8,
                },
            },
        )
        assert status == 201
        wait_id = created["wait"]["id"]
        assert created["wait"]["resume_binding"]["adapter"] == "webhook"

        status, decided = request_json(
            base,
            f"/api/waits/{wait_id}/decision",
            method="POST",
            body={"action": "approve", "actor": "alice"},
        )
        assert status == 200
        assert decided["wait"]["state"] == "approved"
        assert decided["delivery"]["wait_id"] == wait_id
        assert decided["delivery"]["status"] == "pending"
        delivery_id = decided["delivery"]["id"]

        status, listing = request_json(base, "/api/deliveries")
        assert status == 200
        assert [d["id"] for d in listing["deliveries"]] == [delivery_id]

        status, events = request_json(base, f"/api/waits/{wait_id}/events")
        assert status == 200
        assert [e["event_type"] for e in events["events"]][-2:] == [
            "RESUME_REQUESTED",
            "RESUME_DELIVERY_QUEUED",
        ]

        status, replay = request_json(
            base,
            f"/api/waits/{wait_id}/decision",
            method="POST",
            body={"action": "approve", "actor": "alice"},
        )
        assert status == 200
        assert replay["delivery"]["id"] == delivery_id

        status, listing = request_json(base, "/api/deliveries")
        assert len(listing["deliveries"]) == 1

        status, events = request_json(base, f"/api/waits/{wait_id}/events")
        queued = [
            e for e in events["events"]
            if e["event_type"] == "RESUME_DELIVERY_QUEUED"
        ]
        assert len(queued) == 1
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_resume_binding_does_not_materialize_delivery_on_reject(tmp_path):
    queue = HumanQueue(tmp_path / "queue.db")
    httpd = server_module.make_server(queue, host="127.0.0.1", port=0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        status, created = request_json(
            base,
            "/api/waits",
            method="POST",
            body={
                "uri": "human://approve",
                "title": "Reject auto resume?",
                "source": "agent",
                "resume_binding": {
                    "adapter": "webhook",
                    "target": "https://worker.example/resume",
                },
            },
        )
        wait_id = created["wait"]["id"]

        status, decided = request_json(
            base,
            f"/api/waits/{wait_id}/decision",
            method="POST",
            body={"action": "reject", "actor": "alice"},
        )
        assert status == 200
        assert decided["wait"]["state"] == "rejected"
        assert "delivery" not in decided

        status, listing = request_json(base, "/api/deliveries")
        assert status == 200
        assert listing["deliveries"] == []
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_invalid_resume_binding_is_rejected_before_wait_creation(tmp_path):
    queue = HumanQueue(tmp_path / "queue.db")
    httpd = server_module.make_server(queue, host="127.0.0.1", port=0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        status, payload = request_json(
            base,
            "/api/waits",
            method="POST",
            body={
                "uri": "human://approve",
                "title": "Broken binding",
                "source": "agent",
                "resume_binding": {"adapter": "webhook"},
            },
        )
        assert status == 400
        assert payload["error"] == "invalid_resume_binding"

        status, pending = request_json(base, "/api/waits")
        assert pending["waits"] == []

        status, listing = request_json(base, "/api/deliveries")
        assert listing["deliveries"] == []
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_named_destination_auto_materializes_snapshot(tmp_path):
    queue = HumanQueue(tmp_path / "queue.db")
    httpd = server_module.make_server(queue, host="127.0.0.1", port=0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        status, created_dest = request_json(
            base,
            "/api/destinations",
            method="POST",
            body={
                "name": "prod-deploy",
                "adapter": "webhook",
                "target": "https://worker.example/v1",
                "max_attempts": 4,
                "base_delay": 1,
                "multiplier": 2,
                "max_delay": 8,
            },
        )
        assert status == 201
        assert created_dest["destination"]["name"] == "prod-deploy"

        status, created = request_json(
            base,
            "/api/waits",
            method="POST",
            body={
                "uri": "human://approve",
                "title": "Deploy through named destination?",
                "source": "agent",
                "resume_token": "named-http",
                "resume_binding": {"destination": "prod-deploy"},
            },
        )
        assert status == 201
        wait_id = created["wait"]["id"]
        assert created["wait"]["resume_binding"] == {"destination": "prod-deploy"}

        status, decided = request_json(
            base,
            f"/api/waits/{wait_id}/decision",
            method="POST",
            body={"action": "approve", "actor": "alice"},
        )
        assert status == 200
        assert decided["delivery"]["target"] == "https://worker.example/v1"
        delivery_id = decided["delivery"]["id"]

        status, _ = request_json(
            base,
            "/api/destinations",
            method="POST",
            body={
                "name": "prod-deploy",
                "adapter": "webhook",
                "target": "https://worker.example/v2",
            },
        )
        assert status == 201

        status, listing = request_json(base, "/api/deliveries")
        assert status == 200
        job = next(d for d in listing["deliveries"] if d["id"] == delivery_id)
        assert job["target"] == "https://worker.example/v1"
        assert job["destination"] == "prod-deploy"
        assert job["destination_revision"] == 1
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_disabled_destination_blocks_decision_before_commit(tmp_path):
    queue = HumanQueue(tmp_path / "queue.db")
    httpd = server_module.make_server(queue, host="127.0.0.1", port=0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        status, _ = request_json(
            base,
            "/api/destinations",
            method="POST",
            body={
                "name": "prod-deploy",
                "adapter": "webhook",
                "target": "https://worker.example/resume",
            },
        )
        assert status == 201

        status, created = request_json(
            base,
            "/api/waits",
            method="POST",
            body={
                "uri": "human://approve",
                "title": "Governed deploy?",
                "source": "agent",
                "resume_binding": {"destination": "prod-deploy"},
            },
        )
        assert status == 201
        wait_id = created["wait"]["id"]

        status, _ = request_json(
            base,
            "/api/destinations",
            method="POST",
            body={
                "name": "prod-deploy",
                "adapter": "webhook",
                "target": "https://worker.example/resume",
                "enabled": False,
            },
        )
        assert status == 201

        status, blocked = request_json(
            base,
            f"/api/waits/{wait_id}/decision",
            method="POST",
            body={"action": "approve", "actor": "alice"},
        )
        assert status == 409
        assert blocked["error"] == "resume_destination_unavailable"

        status, current = request_json(base, f"/api/waits/{wait_id}")
        assert status == 200
        assert current["wait"]["state"] == "waiting"
        assert current["wait"]["decision"] is None
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_unknown_destination_rejected_at_wait_creation(tmp_path):
    queue = HumanQueue(tmp_path / "queue.db")
    httpd = server_module.make_server(queue, host="127.0.0.1", port=0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        status, payload = request_json(
            base,
            "/api/waits",
            method="POST",
            body={
                "uri": "human://approve",
                "title": "Missing destination",
                "source": "agent",
                "resume_binding": {"destination": "does-not-exist"},
            },
        )
        assert status == 400
        assert payload["error"] == "invalid_resume_binding"
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_destination_routes_separate_read_from_mutation(tmp_path):
    queue = HumanQueue(tmp_path / "queue.db")
    httpd = server_module.make_server(queue, host="127.0.0.1", port=0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        status, listing = request_json(base, "/api/destinations")
        assert status == 200
        assert listing == {"destinations": []}

        status, created = request_json(
            base,
            "/api/destinations",
            method="POST",
            body={
                "name": "read-write-contract",
                "adapter": "webhook",
                "target": "https://worker.example/resume",
            },
        )
        assert status == 201

        status, listing = request_json(base, "/api/destinations")
        assert status == 200
        assert [d["name"] for d in listing["destinations"]] == [
            "read-write-contract"
        ]
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_destination_history_api_and_delivery_revision_snapshot(tmp_path):
    queue = HumanQueue(tmp_path / "queue.db")
    httpd = server_module.make_server(queue, host="127.0.0.1", port=0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        status, first = request_json(
            base,
            "/api/destinations",
            method="POST",
            body={
                "name": "prod-deploy",
                "adapter": "webhook",
                "target": "https://worker.example/v1",
                "max_attempts": 4,
            },
        )
        assert status == 201
        assert first["destination"]["revision"] == 1

        status, created = request_json(
            base,
            "/api/waits",
            method="POST",
            body={
                "uri": "human://approve",
                "title": "Revision snapshot?",
                "source": "agent",
                "resume_binding": {"destination": "prod-deploy"},
            },
        )
        wait_id = created["wait"]["id"]

        status, decided = request_json(
            base,
            f"/api/waits/{wait_id}/decision",
            method="POST",
            body={"action": "approve", "actor": "alice"},
        )
        assert status == 200
        delivery_id = decided["delivery"]["id"]

        status, second = request_json(
            base,
            "/api/destinations",
            method="POST",
            body={
                "name": "prod-deploy",
                "adapter": "webhook",
                "target": "https://worker.example/v2",
                "max_attempts": 4,
            },
        )
        assert status == 201
        assert second["destination"]["revision"] == 2

        status, history = request_json(
            base,
            "/api/destinations/prod-deploy/history",
        )
        assert status == 200
        assert [item["revision"] for item in history["history"]] == [1, 2]

        status, listing = request_json(base, "/api/deliveries")
        job = next(d for d in listing["deliveries"] if d["id"] == delivery_id)
        assert job["target"] == "https://worker.example/v1"

        status, events = request_json(base, f"/api/waits/{wait_id}/events")
        queued = next(
            e for e in events["events"]
            if e["event_type"] == "RESUME_DELIVERY_QUEUED"
        )
        assert queued["data"]["target"] == "https://worker.example/v1"
        assert queued["data"]["destination"] == "prod-deploy"
        assert queued["data"]["destination_revision"] == 1
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_destination_actor_reason_flow_into_delivery_and_audit(tmp_path):
    queue = HumanQueue(tmp_path / "queue.db")
    httpd = server_module.make_server(queue, host="127.0.0.1", port=0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        status, destination = request_json(
            base,
            "/api/destinations",
            method="POST",
            body={
                "name": "prod-deploy",
                "adapter": "webhook",
                "target": "https://worker.example/resume",
                "actor": "release-admin",
                "reason": "CAB-42",
            },
        )
        assert status == 201
        assert destination["destination"]["changed_by"] == "release-admin"
        assert destination["destination"]["change_reason"] == "CAB-42"

        status, created = request_json(
            base,
            "/api/waits",
            method="POST",
            body={
                "uri": "human://approve",
                "title": "Deploy governed release?",
                "source": "agent",
                "resume_binding": {"destination": "prod-deploy"},
            },
        )
        wait_id = created["wait"]["id"]

        status, decided = request_json(
            base,
            f"/api/waits/{wait_id}/decision",
            method="POST",
            body={"action": "approve", "actor": "alice"},
        )
        assert status == 200
        job = decided["delivery"]
        assert job["destination"] == "prod-deploy"
        assert job["destination_revision"] == 1
        assert job["destination_changed_by"] == "release-admin"
        assert job["destination_change_reason"] == "CAB-42"

        status, events = request_json(base, f"/api/waits/{wait_id}/events")
        assert status == 200
        queued = next(
            event
            for event in events["events"]
            if event["event_type"] == "RESUME_DELIVERY_QUEUED"
        )
        assert queued["data"]["destination_changed_by"] == "release-admin"
        assert queued["data"]["destination_change_reason"] == "CAB-42"

        status, history = request_json(
            base,
            "/api/destinations/prod-deploy/history",
        )
        assert status == 200
        assert history["history"][0]["changed_by"] == "release-admin"
        assert history["history"][0]["change_reason"] == "CAB-42"
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_destination_actor_policy_blocks_unauthorized_approve_without_commit(tmp_path):
    queue = HumanQueue(tmp_path / "queue.db")
    httpd = server_module.make_server(queue, host="127.0.0.1", port=0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        status, destination = request_json(
            base,
            "/api/destinations",
            method="POST",
            body={
                "name": "prod-deploy",
                "adapter": "webhook",
                "target": "https://worker.example/resume",
                "actor": "security-admin",
                "reason": "restrict production approvals",
                "allowed_decision_actors": ["alice"],
            },
        )
        assert status == 201
        assert destination["destination"]["allowed_decision_actors"] == ["alice"]

        status, created = request_json(
            base,
            "/api/waits",
            method="POST",
            body={
                "uri": "human://approve",
                "title": "Restricted deploy",
                "source": "agent",
                "resume_binding": {"destination": "prod-deploy"},
            },
        )
        wait_id = created["wait"]["id"]

        status, denied = request_json(
            base,
            f"/api/waits/{wait_id}/decision",
            method="POST",
            body={"action": "approve", "actor": "mallory"},
        )
        assert status == 403
        assert denied["error"] == "actor_not_authorized_for_destination"
        assert denied["actor"] == "mallory"
        assert denied["destination"] == "prod-deploy"
        assert denied["destination_revision"] == 1

        status, current = request_json(base, f"/api/waits/{wait_id}")
        assert status == 200
        assert current["wait"]["state"] == "waiting"
        assert current["wait"]["decision"] is None

        status, events = request_json(base, f"/api/waits/{wait_id}/events")
        event_types = [event["event_type"] for event in events["events"]]
        assert "DECISION_COMMITTED" not in event_types
        assert event_types[-1] == "DECISION_DENIED"
        denied_event = events["events"][-1]
        assert denied_event["actor"] == "mallory"
        assert denied_event["data"]["destination"] == "prod-deploy"
        assert denied_event["data"]["destination_revision"] == 1
        assert denied_event["data"]["allowed_decision_actors"] == ["alice"]

        status, approved = request_json(
            base,
            f"/api/waits/{wait_id}/decision",
            method="POST",
            body={"action": "approve", "actor": "alice"},
        )
        assert status == 200
        assert approved["wait"]["state"] == "approved"
        assert approved["delivery"]["destination_revision"] == 1
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_destination_actor_policy_still_allows_reject_as_safe_exit(tmp_path):
    queue = HumanQueue(tmp_path / "queue.db")
    httpd = server_module.make_server(queue, host="127.0.0.1", port=0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        request_json(
            base,
            "/api/destinations",
            method="POST",
            body={
                "name": "prod-deploy",
                "adapter": "webhook",
                "target": "https://worker.example/resume",
                "allowed_decision_actors": ["alice"],
            },
        )
        _, created = request_json(
            base,
            "/api/waits",
            method="POST",
            body={
                "uri": "human://approve",
                "title": "Reject safely",
                "source": "agent",
                "resume_binding": {"destination": "prod-deploy"},
            },
        )
        wait_id = created["wait"]["id"]

        status, rejected = request_json(
            base,
            f"/api/waits/{wait_id}/decision",
            method="POST",
            body={"action": "reject", "actor": "mallory"},
        )
        assert status == 200
        assert rejected["wait"]["state"] == "rejected"
        assert "delivery" not in rejected
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_authenticated_actor_binding_prevents_body_spoofing(tmp_path):
    queue = HumanQueue(tmp_path / "queue.db")
    authenticator = server_module.ActorAuthenticator(
        {"alice": "token-alice", "bob": "token-bob"}
    )
    httpd = server_module.make_server(
        queue,
        host="127.0.0.1",
        port=0,
        authenticator=authenticator,
    )
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        status, missing = request_json(
            base,
            "/api/destinations",
            method="POST",
            body={
                "name": "prod-deploy",
                "adapter": "webhook",
                "target": "https://worker.example/resume",
                "actor": "alice",
            },
        )
        assert status == 401
        assert missing["error"] == "authentication_required"

        status, created_destination = request_json(
            base,
            "/api/destinations",
            method="POST",
            body={
                "name": "prod-deploy",
                "adapter": "webhook",
                "target": "https://worker.example/resume",
                "actor": "alice",
                "allowed_decision_actors": ["alice"],
            },
            headers={"Authorization": "Bearer token-alice"},
        )
        assert status == 201
        assert created_destination["destination"]["changed_by"] == "alice"

        status, mismatch = request_json(
            base,
            "/api/destinations",
            method="POST",
            body={
                "name": "other",
                "adapter": "webhook",
                "target": "https://worker.example/other",
                "actor": "alice",
            },
            headers={"Authorization": "Bearer token-bob"},
        )
        assert status == 403
        assert mismatch["error"] == "actor_mismatch"

        status, created = request_json(
            base,
            "/api/waits",
            method="POST",
            body={
                "uri": "human://approve",
                "title": "Authenticated deploy",
                "source": "agent",
                "resume_binding": {"destination": "prod-deploy"},
            },
        )
        wait_id = created["wait"]["id"]

        status, spoofed = request_json(
            base,
            f"/api/waits/{wait_id}/decision",
            method="POST",
            body={"action": "approve", "actor": "alice"},
            headers={"Authorization": "Bearer token-bob"},
        )
        assert status == 403
        assert spoofed["error"] == "actor_mismatch"

        status, approved = request_json(
            base,
            f"/api/waits/{wait_id}/decision",
            method="POST",
            body={"action": "approve"},
            headers={"Authorization": "Bearer token-alice"},
        )
        assert status == 200
        assert approved["wait"]["decision"]["actor"] == "alice"
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_machine_callbacks_require_authenticated_machine_identity(tmp_path):
    queue = HumanQueue(tmp_path / "queue.db")
    machine_authenticator = server_module.ActorAuthenticator(
        {"worker-a": "machine-token-a", "worker-b": "machine-token-b"}
    )
    httpd = server_module.make_server(
        queue,
        host="127.0.0.1",
        port=0,
        machine_authenticator=machine_authenticator,
    )
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        item = queue.ask(
            uri="human://approve",
            title="Machine callback auth",
            source="agent",
            resume_token="step-machine",
        )
        queue.decide(item.id, action="approve", actor="alice")

        status, missing = request_json(
            base,
            f"/api/waits/{item.id}/resumed",
            method="POST",
            body={},
        )
        assert status == 401
        assert missing["error"] == "machine_authentication_required"

        status, spoofed = request_json(
            base,
            f"/api/waits/{item.id}/resumed",
            method="POST",
            body={"actor": "worker-a"},
            headers={"Authorization": "Bearer machine-token-b"},
        )
        assert status == 403
        assert spoofed["error"] == "machine_actor_mismatch"

        status, resumed = request_json(
            base,
            f"/api/waits/{item.id}/resumed",
            method="POST",
            body={},
            headers={"Authorization": "Bearer machine-token-a"},
        )
        assert status == 200
        assert resumed["wait"]["execution_state"] == "resumed"

        status, completed = request_json(
            base,
            f"/api/waits/{item.id}/complete",
            method="POST",
            body={"success": True, "detail": "done"},
            headers={"Authorization": "Bearer machine-token-a"},
        )
        assert status == 200
        assert completed["wait"]["execution_state"] == "completed"

        status, events = request_json(base, f"/api/waits/{item.id}/events")
        process_events = [
            event for event in events["events"]
            if event["event_type"] in {"PROCESS_RESUMED", "PROCESS_COMPLETED"}
        ]
        assert [event["actor"] for event in process_events] == [
            "worker-a",
            "worker-a",
        ]
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_human_token_cannot_authenticate_machine_callback(tmp_path):
    queue = HumanQueue(tmp_path / "queue.db")
    human_authenticator = server_module.ActorAuthenticator(
        {"alice": "human-token"}
    )
    machine_authenticator = server_module.ActorAuthenticator(
        {"worker-a": "machine-token"}
    )
    httpd = server_module.make_server(
        queue,
        host="127.0.0.1",
        port=0,
        authenticator=human_authenticator,
        machine_authenticator=machine_authenticator,
    )
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        item = queue.ask(
            uri="human://approve",
            title="Domain separation",
            source="agent",
        )
        queue.decide(item.id, action="approve", actor="alice")

        status, denied = request_json(
            base,
            f"/api/waits/{item.id}/resumed",
            method="POST",
            body={},
            headers={"Authorization": "Bearer human-token"},
        )
        assert status == 401
        assert denied["error"] == "machine_authentication_required"
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_destination_machine_policy_blocks_wrong_machine_without_state_change(tmp_path):
    queue = HumanQueue(tmp_path / "queue.db")
    machine_authenticator = server_module.ActorAuthenticator(
        {"worker-a": "machine-token-a", "worker-b": "machine-token-b"}
    )
    httpd = server_module.make_server(
        queue,
        host="127.0.0.1",
        port=0,
        machine_authenticator=machine_authenticator,
    )
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        status, destination = request_json(
            base,
            "/api/destinations",
            method="POST",
            body={
                "name": "prod-deploy",
                "adapter": "webhook",
                "target": "https://worker.example/resume",
                "allowed_machine_actors": ["worker-a"],
            },
        )
        assert status == 201
        assert destination["destination"]["allowed_machine_actors"] == ["worker-a"]

        status, created = request_json(
            base,
            "/api/waits",
            method="POST",
            body={
                "uri": "human://approve",
                "title": "Machine-bound deploy",
                "source": "agent",
                "resume_binding": {"destination": "prod-deploy"},
            },
        )
        wait_id = created["wait"]["id"]

        status, decided = request_json(
            base,
            f"/api/waits/{wait_id}/decision",
            method="POST",
            body={"action": "approve", "actor": "alice"},
        )
        assert status == 200
        assert decided["delivery"]["allowed_machine_actors"] == ["worker-a"]

        status, denied = request_json(
            base,
            f"/api/waits/{wait_id}/resumed",
            method="POST",
            body={},
            headers={"Authorization": "Bearer machine-token-b"},
        )
        assert status == 403
        assert denied["error"] == "machine_not_authorized_for_delivery"

        status, current = request_json(base, f"/api/waits/{wait_id}")
        assert status == 200
        assert current["wait"]["execution_state"] == "resume_requested"

        status, events = request_json(base, f"/api/waits/{wait_id}/events")
        event_types = [event["event_type"] for event in events["events"]]
        assert event_types[-1] == "MACHINE_CALLBACK_DENIED"
        assert "PROCESS_RESUMED" not in event_types
        denied_event = events["events"][-1]
        assert denied_event["actor"] == "worker-b"
        assert denied_event["data"]["callback"] == "resumed"
        assert denied_event["data"]["destination"] == "prod-deploy"
        assert denied_event["data"]["destination_revision"] == 1
        assert denied_event["data"]["allowed_machine_actors"] == ["worker-a"]

        status, resumed = request_json(
            base,
            f"/api/waits/{wait_id}/resumed",
            method="POST",
            body={},
            headers={"Authorization": "Bearer machine-token-a"},
        )
        assert status == 200
        assert resumed["wait"]["execution_state"] == "resumed"

        status, completed = request_json(
            base,
            f"/api/waits/{wait_id}/complete",
            method="POST",
            body={"success": True},
            headers={"Authorization": "Bearer machine-token-a"},
        )
        assert status == 200
        assert completed["wait"]["execution_state"] == "completed"
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_machine_policy_snapshot_does_not_drift_after_destination_change(tmp_path):
    queue = HumanQueue(tmp_path / "queue.db")
    machine_authenticator = server_module.ActorAuthenticator(
        {"worker-a": "machine-token-a", "worker-b": "machine-token-b"}
    )
    httpd = server_module.make_server(
        queue,
        host="127.0.0.1",
        port=0,
        machine_authenticator=machine_authenticator,
    )
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        request_json(
            base,
            "/api/destinations",
            method="POST",
            body={
                "name": "prod-deploy",
                "adapter": "webhook",
                "target": "https://worker.example/resume",
                "allowed_machine_actors": ["worker-a"],
            },
        )
        _, created = request_json(
            base,
            "/api/waits",
            method="POST",
            body={
                "uri": "human://approve",
                "title": "Immutable machine policy",
                "source": "agent",
                "resume_binding": {"destination": "prod-deploy"},
            },
        )
        wait_id = created["wait"]["id"]
        status, decided = request_json(
            base,
            f"/api/waits/{wait_id}/decision",
            method="POST",
            body={"action": "approve", "actor": "alice"},
        )
        assert status == 200
        assert decided["delivery"]["destination_revision"] == 1
        assert decided["delivery"]["allowed_machine_actors"] == ["worker-a"]

        request_json(
            base,
            "/api/destinations",
            method="POST",
            body={
                "name": "prod-deploy",
                "adapter": "webhook",
                "target": "https://worker.example/resume",
                "allowed_machine_actors": ["worker-b"],
            },
        )

        status, denied = request_json(
            base,
            f"/api/waits/{wait_id}/resumed",
            method="POST",
            body={},
            headers={"Authorization": "Bearer machine-token-b"},
        )
        assert status == 403
        assert denied["error"] == "machine_not_authorized_for_delivery"

        status, resumed = request_json(
            base,
            f"/api/waits/{wait_id}/resumed",
            method="POST",
            body={},
            headers={"Authorization": "Bearer machine-token-a"},
        )
        assert status == 200
        assert resumed["wait"]["execution_state"] == "resumed"
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_custom_header_auth_provider_drives_human_policy_without_bearer_tokens(tmp_path):
    class HeaderProvider:
        def authenticate(self, context, *, claimed_actor=None):
            actor = context.headers.get("X-Verified-Actor")
            if not actor:
                raise server_module.AuthenticationError("verified actor header required")
            if claimed_actor and claimed_actor != actor:
                raise server_module.ActorMismatchError("claimed actor mismatch")
            return type(
                "Principal",
                (),
                {
                    "actor": actor,
                    "kind": "human",
                    "provider": "trusted-proxy",
                },
            )()

    queue = HumanQueue(tmp_path / "queue.db")
    httpd = server_module.make_server(
        queue,
        host="127.0.0.1",
        port=0,
        human_auth_provider=HeaderProvider(),
    )
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        status, destination = request_json(
            base,
            "/api/destinations",
            method="POST",
            body={
                "name": "proxy-governed",
                "adapter": "webhook",
                "target": "https://worker.example/resume",
                "allowed_decision_actors": ["alice"],
            },
            headers={"X-Verified-Actor": "alice"},
        )
        assert status == 201
        assert destination["destination"]["changed_by"] == "alice"

        status, created = request_json(
            base,
            "/api/waits",
            method="POST",
            body={
                "uri": "human://approve",
                "title": "Proxy-authenticated approval",
                "source": "agent",
                "resume_binding": {"destination": "proxy-governed"},
            },
        )
        wait_id = created["wait"]["id"]

        status, denied = request_json(
            base,
            f"/api/waits/{wait_id}/decision",
            method="POST",
            body={"action": "approve"},
            headers={"X-Verified-Actor": "mallory"},
        )
        assert status == 403
        assert denied["error"] == "actor_not_authorized_for_destination"

        status, approved = request_json(
            base,
            f"/api/waits/{wait_id}/decision",
            method="POST",
            body={"action": "approve"},
            headers={"X-Verified-Actor": "alice"},
        )
        assert status == 200
        assert approved["wait"]["decision"]["actor"] == "alice"
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_auth_provider_principal_kind_is_enforced(tmp_path):
    class WrongKindProvider:
        def authenticate(self, context, *, claimed_actor=None):
            return type(
                "Principal",
                (),
                {
                    "actor": "worker-a",
                    "kind": "machine",
                    "provider": "wrong-domain",
                },
            )()

    queue = HumanQueue(tmp_path / "queue.db")
    httpd = server_module.make_server(
        queue,
        host="127.0.0.1",
        port=0,
        human_auth_provider=WrongKindProvider(),
    )
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        status, payload = request_json(
            base,
            "/api/destinations",
            method="POST",
            body={
                "name": "wrong-kind",
                "adapter": "webhook",
                "target": "https://worker.example/resume",
            },
        )
        assert status == 401
        assert payload["error"] == "authentication_required"
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()
