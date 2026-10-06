import importlib.util
import json
import sys
import threading
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


ROOT = Path(__file__).parents[1] / "human-queue"


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


def request_json(base, path, *, method="GET", body=None):
    data = None if body is None else json.dumps(body).encode()
    request = Request(
        base + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
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
