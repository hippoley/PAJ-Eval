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
