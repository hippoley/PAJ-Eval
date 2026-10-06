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
GitHubRepositoryDispatchAdapter = adapters.GitHubRepositoryDispatchAdapter
RetryPolicy = adapters.RetryPolicy
dispatch_with_retry = adapters.dispatch_with_retry
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


def test_github_repository_dispatch_adapter_sends_expected_payload(tmp_path):
    received = {}

    class Receiver(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            return

        def do_POST(self):
            received["path"] = self.path
            received["authorization"] = self.headers.get("Authorization")
            received["accept"] = self.headers.get("Accept")
            length = int(self.headers.get("Content-Length", "0"))
            received["body"] = json.loads(self.rfile.read(length))
            self.send_response(204)
            self.end_headers()

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Receiver)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    try:
        q = HumanQueue(tmp_path / "queue.db")
        item = q.ask(
            uri="human://approve",
            title="Deploy GitHub workflow?",
            source="ci",
            resume_token="deploy-step-7",
        )
        decided = q.decide(item.id, action="approve", actor="alice")
        adapter = GitHubRepositoryDispatchAdapter(
            "acme/app",
            token="gh-secret",
            event_type="humanqueue-resume",
            api_base=f"http://127.0.0.1:{httpd.server_address[1]}",
        )

        result = adapter.dispatch(q, decided)

        assert result["status"] == 204
        assert received["path"] == "/repos/acme/app/dispatches"
        assert received["authorization"] == "Bearer gh-secret"
        assert received["accept"] == "application/vnd.github+json"
        assert received["body"]["event_type"] == "humanqueue-resume"
        payload = received["body"]["client_payload"]
        assert payload["wait_id"] == item.id
        assert payload["resume_token"] == "deploy-step-7"
        assert payload["decision"]["action"] == "approve"

        events = q.audit_events(item.id)
        assert events[-1].event_type == "RESUME_DISPATCHED"
        assert events[-1].data == {
            "adapter": "github_repository_dispatch",
            "target": "github://acme/app/humanqueue-resume",
        }
        assert "gh-secret" not in json.dumps([event.data for event in events])
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_github_repository_dispatch_validates_repository_name():
    try:
        GitHubRepositoryDispatchAdapter("invalid", token="x")
    except ValueError as exc:
        assert "owner/name" in str(exc)
    else:
        raise AssertionError("invalid repository name unexpectedly accepted")


def test_retry_policy_recovers_after_transient_failures(tmp_path):
    calls = {"count": 0}

    class FlakyReceiver(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            return

        def do_POST(self):
            calls["count"] += 1
            if calls["count"] < 3:
                self.send_response(503)
                self.end_headers()
                self.wfile.write(b"temporary")
                return
            self.send_response(204)
            self.end_headers()

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), FlakyReceiver)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    try:
        q = HumanQueue(tmp_path / "queue.db")
        item = q.ask(uri="human://approve", title="Retry me", source="agent")
        decided = q.decide(item.id, action="approve", actor="alice")
        adapter = GenericWebhookAdapter(
            f"http://127.0.0.1:{httpd.server_address[1]}/resume"
        )
        delays = []

        result = dispatch_with_retry(
            q,
            decided,
            adapter,
            policy=RetryPolicy(
                max_attempts=3,
                base_delay=0.01,
                multiplier=2,
                max_delay=0.1,
            ),
            sleeper=delays.append,
        )

        assert result["status"] == 204
        assert calls["count"] == 3
        assert delays == [0.01, 0.02]

        events = q.audit_events(item.id)
        types = [e.event_type for e in events]
        assert types.count("RESUME_DELIVERY_ATTEMPT") == 3
        assert types.count("RESUME_DELIVERY_FAILED") == 2
        assert types.count("RESUME_DISPATCHED") == 1
        assert "RESUME_DEAD_LETTERED" not in types
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_retry_policy_dead_letters_after_final_failure(tmp_path):
    class BrokenReceiver(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            return

        def do_POST(self):
            self.send_response(503)
            self.end_headers()

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), BrokenReceiver)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    try:
        q = HumanQueue(tmp_path / "queue.db")
        item = q.ask(uri="human://approve", title="Fail me", source="agent")
        decided = q.decide(item.id, action="approve", actor="alice")
        adapter = GenericWebhookAdapter(
            f"http://127.0.0.1:{httpd.server_address[1]}/resume"
        )

        try:
            dispatch_with_retry(
                q,
                decided,
                adapter,
                policy=RetryPolicy(max_attempts=2, base_delay=0, max_delay=0),
                sleeper=lambda _: None,
            )
        except Exception:
            pass
        else:
            raise AssertionError("delivery unexpectedly succeeded")

        events = q.audit_events(item.id)
        types = [e.event_type for e in events]
        assert types.count("RESUME_DELIVERY_ATTEMPT") == 2
        assert types.count("RESUME_DELIVERY_FAILED") == 1
        assert types.count("RESUME_DEAD_LETTERED") == 1
        assert "RESUME_DISPATCHED" not in types

        dead = next(e for e in events if e.event_type == "RESUME_DEAD_LETTERED")
        assert dead.data["attempt"] == 2
        assert "HTTP Error 503" in dead.data["error"]
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def test_retry_policy_backoff_is_bounded():
    policy = RetryPolicy(
        max_attempts=5,
        base_delay=0.5,
        multiplier=3,
        max_delay=2,
    )
    assert [policy.delay_for(i) for i in range(1, 5)] == [0.5, 1.5, 2, 2]
