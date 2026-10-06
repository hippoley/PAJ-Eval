import importlib.util
import os
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1] / "human-queue"
sys.path.insert(0, str(ROOT))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


auth = load("human_queue_auth", ROOT / "auth.py")
ActorAuthenticator = auth.ActorAuthenticator
AuthenticationError = auth.AuthenticationError
ActorMismatchError = auth.ActorMismatchError
AuthContext = auth.AuthContext
Principal = auth.Principal
BearerTokenAuthProvider = auth.BearerTokenAuthProvider
adapt_authenticator = auth.adapt_authenticator
ensure_disjoint_authenticators = auth.ensure_disjoint_authenticators
ensure_disjoint_providers = auth.ensure_disjoint_providers


def test_authenticator_maps_bearer_token_to_actor():
    authenticator = ActorAuthenticator(
        {"alice": "token-a", "bob": "token-b"}
    )
    assert authenticator.authenticate("Bearer token-a") == "alice"
    assert authenticator.authenticate(
        "Bearer token-b",
        claimed_actor="bob",
    ) == "bob"


def test_authenticator_rejects_missing_invalid_and_spoofed_actor():
    authenticator = ActorAuthenticator({"alice": "token-a"})

    with pytest.raises(AuthenticationError):
        authenticator.authenticate(None)

    with pytest.raises(AuthenticationError):
        authenticator.authenticate("Bearer wrong")

    with pytest.raises(ActorMismatchError):
        authenticator.authenticate(
            "Bearer token-a",
            claimed_actor="mallory",
        )


def test_authenticator_rejects_duplicate_tokens():
    with pytest.raises(ValueError, match="unique"):
        ActorAuthenticator(
            {"alice": "same-token", "bob": "same-token"}
        )


def test_authenticator_loads_optional_env(monkeypatch):
    monkeypatch.delenv("HUMANQUEUE_ACTOR_TOKENS", raising=False)
    assert ActorAuthenticator.from_env() is None

    monkeypatch.setenv(
        "HUMANQUEUE_ACTOR_TOKENS",
        '{"alice":"token-a","bob":"token-b"}',
    )
    loaded = ActorAuthenticator.from_env()
    assert loaded is not None
    assert loaded.authenticate("Bearer token-b") == "bob"


def test_authenticator_rejects_invalid_env_shape(monkeypatch):
    monkeypatch.setenv("HUMANQUEUE_ACTOR_TOKENS", '["not","an","object"]')
    with pytest.raises(ValueError, match="JSON object"):
        ActorAuthenticator.from_env()


def test_human_and_machine_token_domains_must_be_disjoint():
    human = ActorAuthenticator({"alice": "human-token"})
    machine = ActorAuthenticator({"worker-a": "machine-token"})
    ensure_disjoint_authenticators(human, machine)

    overlapping = ActorAuthenticator({"worker-a": "human-token"})
    with pytest.raises(ValueError, match="must not share"):
        ensure_disjoint_authenticators(human, overlapping)


def test_machine_authenticator_can_load_separate_env(monkeypatch):
    monkeypatch.setenv(
        "HUMANQUEUE_MACHINE_TOKENS",
        '{"worker-a":"machine-token"}',
    )
    machine = ActorAuthenticator.from_env("HUMANQUEUE_MACHINE_TOKENS")
    assert machine is not None
    assert machine.authenticate("Bearer machine-token") == "worker-a"


def test_bearer_provider_returns_typed_principal():
    provider = BearerTokenAuthProvider(
        ActorAuthenticator({"alice": "token-a"}),
        principal_kind="human",
        provider_name="local-test",
    )
    principal = provider.authenticate(AuthContext("Bearer token-a"))
    assert principal == Principal(
        actor="alice",
        kind="human",
        provider="local-test",
        attributes={},
    )


def test_legacy_authenticator_can_be_adapted_without_breaking_api():
    authenticator = ActorAuthenticator({"worker-a": "machine-token"})
    provider = adapt_authenticator(
        authenticator,
        principal_kind="machine",
    )
    assert provider is not None
    principal = provider.authenticate(AuthContext("Bearer machine-token"))
    assert principal.actor == "worker-a"
    assert principal.kind == "machine"


def test_disjoint_provider_check_applies_to_local_bearer_providers():
    human = BearerTokenAuthProvider(
        ActorAuthenticator({"alice": "shared-token"}),
        principal_kind="human",
    )
    machine = BearerTokenAuthProvider(
        ActorAuthenticator({"worker-a": "shared-token"}),
        principal_kind="machine",
    )
    with pytest.raises(ValueError, match="must not share"):
        ensure_disjoint_providers(human, machine)
