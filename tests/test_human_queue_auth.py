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
TrustedHeaderAuthProvider = auth.TrustedHeaderAuthProvider
load_auth_provider = auth.load_auth_provider
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


def test_trusted_header_provider_requires_proxy_proof_and_actor():
    provider = TrustedHeaderAuthProvider(
        principal_kind="human",
        proof_secret="proxy-secret",
        actor_header="X-Verified-Actor",
        proof_header="X-Proxy-Proof",
    )

    with pytest.raises(AuthenticationError, match="proxy proof"):
        provider.authenticate(
            AuthContext(
                authorization=None,
                headers={"X-Verified-Actor": "alice"},
            )
        )

    with pytest.raises(AuthenticationError, match="actor header"):
        provider.authenticate(
            AuthContext(
                authorization=None,
                headers={"X-Proxy-Proof": "proxy-secret"},
            )
        )

    principal = provider.authenticate(
        AuthContext(
            authorization=None,
            headers={
                "X-Verified-Actor": "alice",
                "X-Proxy-Proof": "proxy-secret",
            },
        )
    )
    assert principal == Principal(
        actor="alice",
        kind="human",
        provider="trusted-header",
        attributes={},
    )


def test_trusted_header_provider_rejects_claimed_actor_spoof():
    provider = TrustedHeaderAuthProvider(
        principal_kind="human",
        proof_secret="proxy-secret",
    )
    with pytest.raises(ActorMismatchError):
        provider.authenticate(
            AuthContext(
                authorization=None,
                headers={
                    "X-HumanQueue-Actor": "alice",
                    "X-HumanQueue-Proxy-Secret": "proxy-secret",
                },
            ),
            claimed_actor="mallory",
        )


def test_auth_provider_factory_preserves_legacy_bearer_mode(monkeypatch):
    monkeypatch.delenv("HUMANQUEUE_HUMAN_AUTH_PROVIDER", raising=False)
    monkeypatch.setenv(
        "HUMANQUEUE_ACTOR_TOKENS",
        '{"alice":"token-a"}',
    )
    provider = load_auth_provider("human")
    assert isinstance(provider, BearerTokenAuthProvider)
    principal = provider.authenticate(AuthContext("Bearer token-a"))
    assert principal.actor == "alice"
    assert principal.kind == "human"


def test_auth_provider_factory_loads_trusted_header_mode(monkeypatch):
    monkeypatch.setenv(
        "HUMANQUEUE_HUMAN_AUTH_PROVIDER",
        "trusted-header",
    )
    monkeypatch.setenv(
        "HUMANQUEUE_HUMAN_PROXY_SECRET",
        "proxy-secret",
    )
    monkeypatch.setenv(
        "HUMANQUEUE_HUMAN_ACTOR_HEADER",
        "X-Verified-Human",
    )
    provider = load_auth_provider("human")
    assert isinstance(provider, TrustedHeaderAuthProvider)

    principal = provider.authenticate(
        AuthContext(
            authorization=None,
            headers={
                "X-Verified-Human": "alice",
                "X-HumanQueue-Proxy-Secret": "proxy-secret",
            },
        )
    )
    assert principal.actor == "alice"


def test_provider_factory_requires_credentials_for_explicit_mode(monkeypatch):
    monkeypatch.setenv("HUMANQUEUE_HUMAN_AUTH_PROVIDER", "bearer")
    monkeypatch.delenv("HUMANQUEUE_ACTOR_TOKENS", raising=False)
    with pytest.raises(ValueError, match="required for bearer auth"):
        load_auth_provider("human")

    monkeypatch.setenv(
        "HUMANQUEUE_HUMAN_AUTH_PROVIDER",
        "trusted-header",
    )
    monkeypatch.delenv("HUMANQUEUE_HUMAN_PROXY_SECRET", raising=False)
    with pytest.raises(ValueError, match="proof_secret"):
        load_auth_provider("human")


def test_human_machine_provider_secrets_must_be_disjoint():
    human = TrustedHeaderAuthProvider(
        principal_kind="human",
        proof_secret="shared-secret",
    )
    machine = TrustedHeaderAuthProvider(
        principal_kind="machine",
        proof_secret="shared-secret",
    )
    with pytest.raises(ValueError, match="must not share credentials"):
        ensure_disjoint_providers(human, machine)
