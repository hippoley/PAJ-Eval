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
