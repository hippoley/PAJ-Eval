import importlib.util
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).parents[1] / "human-queue"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


runtime = load("runtime", ROOT / "runtime.py")
adapters = load("human_queue_adapters", ROOT / "adapters.py")
HumanQueue = runtime.HumanQueue
GenericWebhookAdapter = adapters.GenericWebhookAdapter
sanitize_target = adapters.sanitize_target


def test_webhook_adapter_delivers_decision_without_claiming_machine_resumed(tmp_path):
    received = {}

    class Receiver(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            return

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            received["body"] = json.loads(self.rfile.read(length))
            received["authorization"] = self.headers.get("Authorization")
            self.send_response(202)
            self.end_headers()
            self.wfile.write(b"accepted")

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Receiver)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    try:
        q = HumanQueue(tmp_path / "queue.db")
        item = q.ask(
            uri="human://approve",
            title="Deploy?",
            source="ci",
            resume_token="deploy-42",
        )
        decided = q.decide(item.id, action="approve", actor="alice")

        adapter = GenericWebhookAdapter(
            f"http://127.0.0.1:{httpd.server_address[1]}/resume?secret=hidden",
            bearer_token="top-secret",
        )
        result = adapter.dispatch(q, decided)

        assert result["status"] == 202
        assert received["body"]["wait_id"] == item.id
        assert received["body"]["resume_token"] == "deploy-42"
        assert received["body"]["decision"]["action"] == "approve"
        assert received["authorization"] == "Bearer top-secret"

        persisted = q.get(item.id)
        assert persisted.execution_state == "resume_requested"

        events = q.audit_events(item.id)
        assert events[-1].event_type == "RESUME_DISPATCHED"
        assert events[-1].data["adapter"] == "webhook"
        assert "secret=hidden" not in events[-1].data["target"]
        assert "top-secret" not in json.dumps(events[-1].data)
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_webhook_dispatch_is_idempotent_in_audit_log(tmp_path):
    class Receiver(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            return

        def do_POST(self):
            self.send_response(204)
            self.end_headers()

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Receiver)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    try:
        q = HumanQueue(tmp_path / "queue.db")
        item = q.ask(uri="human://approve", title="Run?", source="agent")
        decided = q.decide(item.id, action="approve", actor="alice")
        adapter = GenericWebhookAdapter(
            f"http://127.0.0.1:{httpd.server_address[1]}/resume"
        )

        adapter.dispatch(q, decided)
        adapter.dispatch(q, q.get(item.id))

        events = q.audit_events(item.id)
        assert [e.event_type for e in events].count("RESUME_DISPATCHED") == 1
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_rejected_decision_cannot_be_dispatched(tmp_path):
    q = HumanQueue(tmp_path / "queue.db")
    item = q.ask(uri="human://approve", title="No?", source="agent")
    rejected = q.decide(item.id, action="reject", actor="alice")
    adapter = GenericWebhookAdapter("http://127.0.0.1:9/resume", timeout=0.01)

    try:
        adapter.dispatch(q, rejected)
    except RuntimeError as exc:
        assert "no resume request" in str(exc)
    else:
        raise AssertionError("rejected wait unexpectedly dispatched")


def test_sanitize_target_removes_credentials_query_and_fragment():
    safe = sanitize_target("https://user:pass@example.com:8443/resume?q=secret#frag")
    assert safe == "https://example.com:8443/resume"
