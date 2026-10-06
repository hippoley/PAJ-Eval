import importlib.util
import sys
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


destinations = load("human_queue_destinations", ROOT / "destinations.py")
DestinationRegistry = destinations.DestinationRegistry
RetryPolicy = destinations.RetryPolicy
resolve_resume_binding = destinations.resolve_resume_binding


def test_destination_registry_persists_and_updates_without_secrets(tmp_path):
    db = tmp_path / "queue.db"
    registry = DestinationRegistry(db)

    first = registry.put(
        "prod-deploy",
        adapter="webhook",
        target="https://worker.example/resume",
        policy=RetryPolicy(max_attempts=4, base_delay=1, multiplier=2, max_delay=8),
        now=100,
    )
    assert first.name == "prod-deploy"
    assert first.enabled is True
    assert first.created_at == 100

    reopened = DestinationRegistry(db)
    loaded = reopened.get("prod-deploy", require_enabled=True)
    assert loaded.target == "https://worker.example/resume"
    assert loaded.policy.max_attempts == 4

    updated = reopened.put(
        "prod-deploy",
        adapter="webhook",
        target="https://worker.example/v2",
        policy=RetryPolicy(max_attempts=5),
        now=200,
    )
    assert updated.created_at == 100
    assert updated.updated_at == 200
    assert updated.target.endswith("/v2")
    assert [item.name for item in reopened.list()] == ["prod-deploy"]


def test_disabled_destination_fails_closed(tmp_path):
    registry = DestinationRegistry(tmp_path / "queue.db")
    registry.put(
        "prod-deploy",
        adapter="webhook",
        target="https://worker.example/resume",
    )
    registry.set_enabled("prod-deploy", False)

    try:
        registry.get("prod-deploy", require_enabled=True)
    except RuntimeError as exc:
        assert "disabled" in str(exc)
    else:
        raise AssertionError("disabled destination unexpectedly resolved")


def test_named_binding_resolves_to_immutable_snapshot(tmp_path):
    registry = DestinationRegistry(tmp_path / "queue.db")
    registry.put(
        "github-release",
        adapter="github_repository_dispatch",
        target="github://acme/app/humanqueue-resume",
        policy=RetryPolicy(max_attempts=4, base_delay=1, multiplier=2, max_delay=8),
    )

    snapshot = resolve_resume_binding(
        {"destination": "github-release"},
        registry,
    )
    assert snapshot == {
        "destination": "github-release",
        "adapter": "github_repository_dispatch",
        "target": "github://acme/app/humanqueue-resume",
        "max_attempts": 4,
        "base_delay": 1,
        "multiplier": 2,
        "max_delay": 8,
    }

    registry.put(
        "github-release",
        adapter="github_repository_dispatch",
        target="github://acme/app/new-event",
    )
    assert snapshot["target"] == "github://acme/app/humanqueue-resume"


def test_raw_binding_remains_backward_compatible(tmp_path):
    registry = DestinationRegistry(tmp_path / "queue.db")
    snapshot = resolve_resume_binding(
        {
            "adapter": "webhook",
            "target": "https://worker.example/resume",
            "max_attempts": 2,
        },
        registry,
    )
    assert snapshot["adapter"] == "webhook"
    assert snapshot["target"] == "https://worker.example/resume"
    assert snapshot["max_attempts"] == 2


def test_webhook_destination_strips_url_secrets_before_persisting(tmp_path):
    registry = DestinationRegistry(tmp_path / "queue.db")
    item = registry.put(
        "secret-free",
        adapter="webhook",
        target="https://user:pass@example.com:8443/resume?token=secret#frag",
    )

    assert item.target == "https://example.com:8443/resume"
    reopened = DestinationRegistry(tmp_path / "queue.db")
    assert reopened.get("secret-free").target == "https://example.com:8443/resume"


def test_destination_revision_only_changes_when_configuration_changes(tmp_path):
    registry = DestinationRegistry(tmp_path / "queue.db")

    first = registry.put(
        "prod-deploy",
        adapter="webhook",
        target="https://worker.example/v1",
        policy=RetryPolicy(max_attempts=4),
        now=100,
    )
    same = registry.put(
        "prod-deploy",
        adapter="webhook",
        target="https://worker.example/v1",
        policy=RetryPolicy(max_attempts=4),
        now=110,
    )
    changed = registry.put(
        "prod-deploy",
        adapter="webhook",
        target="https://worker.example/v2",
        policy=RetryPolicy(max_attempts=4),
        now=120,
    )

    assert first.revision == 1
    assert same.revision == 1
    assert changed.revision == 2
    assert [item.revision for item in registry.history("prod-deploy")] == [1, 2]
    assert [item.target for item in registry.history("prod-deploy")] == [
        "https://worker.example/v1",
        "https://worker.example/v2",
    ]


def test_enable_disable_changes_destination_revision(tmp_path):
    registry = DestinationRegistry(tmp_path / "queue.db")
    created = registry.put(
        "prod-deploy",
        adapter="webhook",
        target="https://worker.example/resume",
        now=100,
    )
    disabled = registry.set_enabled("prod-deploy", False, now=110)
    enabled = registry.set_enabled("prod-deploy", True, now=120)

    assert created.revision == 1
    assert disabled.revision == 2
    assert enabled.revision == 3
    assert [item.enabled for item in registry.history("prod-deploy")] == [
        True,
        False,
        True,
    ]


def test_named_binding_snapshot_contains_destination_revision(tmp_path):
    registry = DestinationRegistry(tmp_path / "queue.db")
    registry.put(
        "github-release",
        adapter="github_repository_dispatch",
        target="github://acme/app/humanqueue-resume",
    )
    snapshot = resolve_resume_binding(
        {"destination": "github-release"},
        registry,
    )

    assert snapshot["destination"] == "github-release"
    assert snapshot["destination_revision"] == 1
