import base64
import hashlib
import hmac
import importlib.util
import json
import os
import sys
import time
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
Hs256JwtAuthProvider = auth.Hs256JwtAuthProvider
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


def _jwt(secret, claims, *, kid="k1", alg="HS256"):
    header = {"alg": alg, "typ": "JWT", "kid": kid}
    def enc(value):
        raw = json.dumps(value, separators=(",", ":"), sort_keys=True).encode()
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
    head = enc(header)
    body = enc(claims)
    sig = hmac.new(
        secret.encode(),
        f"{head}.{body}".encode(),
        hashlib.sha256,
    ).digest()
    signature = base64.urlsafe_b64encode(sig).rstrip(b"=").decode()
    return f"{head}.{body}.{signature}"


def test_hs256_jwt_provider_authenticates_signed_principal():
    now = time.time()
    provider = Hs256JwtAuthProvider(
        principal_kind="human",
        keys={"k1": "secret-one", "k2": "secret-two"},
        issuer="https://issuer.example",
        audience="humanqueue",
        leeway_seconds=0,
    )
    token = _jwt(
        "secret-two",
        {
            "iss": "https://issuer.example",
            "aud": "humanqueue",
            "sub": "alice",
            "exp": now + 60,
        },
        kid="k2",
    )
    principal = provider.authenticate(AuthContext(f"Bearer {token}"))
    assert principal.actor == "alice"
    assert principal.kind == "human"
    assert principal.provider == "jwt-hs256"
    assert principal.attributes == {
        "issuer": "https://issuer.example",
        "audience": "humanqueue",
        "kid": "k2",
    }


@pytest.mark.parametrize(
    "mutator,error",
    [
        (lambda c, now: {**c, "iss": "https://evil.example"}, "issuer"),
        (lambda c, now: {**c, "aud": "other"}, "audience"),
        (lambda c, now: {**c, "exp": now - 1}, "expired"),
        (lambda c, now: {**c, "nbf": now + 60}, "not yet valid"),
    ],
)
def test_hs256_jwt_provider_rejects_invalid_claims(mutator, error):
    now = time.time()
    provider = Hs256JwtAuthProvider(
        principal_kind="human",
        keys={"k1": "secret-one"},
        issuer="https://issuer.example",
        audience="humanqueue",
        leeway_seconds=0,
    )
    claims = {
        "iss": "https://issuer.example",
        "aud": "humanqueue",
        "sub": "alice",
        "exp": now + 60,
    }
    token = _jwt("secret-one", mutator(claims, now))
    with pytest.raises(AuthenticationError, match=error):
        provider.authenticate(AuthContext(f"Bearer {token}"))


def test_hs256_jwt_provider_rejects_wrong_signature_unknown_kid_and_alg():
    now = time.time()
    provider = Hs256JwtAuthProvider(
        principal_kind="machine",
        keys={"k1": "secret-one"},
        issuer="issuer",
        audience="aud",
        leeway_seconds=0,
    )
    claims = {
        "iss": "issuer",
        "aud": "aud",
        "sub": "worker-a",
        "exp": now + 60,
    }

    wrong_signature = _jwt("wrong-secret", claims)
    with pytest.raises(AuthenticationError, match="signature"):
        provider.authenticate(AuthContext(f"Bearer {wrong_signature}"))

    unknown_kid = _jwt("secret-two", claims, kid="k2")
    with pytest.raises(AuthenticationError, match="unknown JWT kid"):
        provider.authenticate(AuthContext(f"Bearer {unknown_kid}"))

    wrong_alg = _jwt("secret-one", claims, alg="HS512")
    with pytest.raises(AuthenticationError, match="alg"):
        provider.authenticate(AuthContext(f"Bearer {wrong_alg}"))


def test_hs256_jwt_provider_rejects_actor_spoof():
    now = time.time()
    provider = Hs256JwtAuthProvider(
        principal_kind="human",
        keys={"k1": "secret-one"},
        issuer="issuer",
        audience="aud",
    )
    token = _jwt(
        "secret-one",
        {
            "iss": "issuer",
            "aud": "aud",
            "sub": "alice",
            "exp": now + 60,
        },
    )
    with pytest.raises(ActorMismatchError):
        provider.authenticate(
            AuthContext(f"Bearer {token}"),
            claimed_actor="mallory",
        )


def test_auth_provider_factory_loads_hs256_jwt(monkeypatch):
    monkeypatch.setenv("HUMANQUEUE_HUMAN_AUTH_PROVIDER", "jwt-hs256")
    monkeypatch.setenv(
        "HUMANQUEUE_HUMAN_JWT_KEYS",
        '{"current":"secret-current","previous":"secret-previous"}',
    )
    monkeypatch.setenv(
        "HUMANQUEUE_HUMAN_JWT_ISSUER",
        "https://issuer.example",
    )
    monkeypatch.setenv(
        "HUMANQUEUE_HUMAN_JWT_AUDIENCE",
        "humanqueue",
    )
    provider = load_auth_provider("human")
    assert isinstance(provider, Hs256JwtAuthProvider)
    assert set(provider.keys) == {"current", "previous"}


def test_hs256_jwt_provider_enforces_max_token_age_and_iat():
    now = time.time()
    provider = Hs256JwtAuthProvider(
        principal_kind="human",
        keys={"k1": "secret-one"},
        issuer="issuer",
        audience="aud",
        leeway_seconds=0,
        max_token_age_seconds=30,
    )

    missing_iat = _jwt(
        "secret-one",
        {
            "iss": "issuer",
            "aud": "aud",
            "sub": "alice",
            "exp": now + 60,
        },
    )
    with pytest.raises(AuthenticationError, match="iat is required"):
        provider.authenticate(AuthContext(f"Bearer {missing_iat}"))

    stale = _jwt(
        "secret-one",
        {
            "iss": "issuer",
            "aud": "aud",
            "sub": "alice",
            "iat": now - 31,
            "exp": now + 60,
        },
    )
    with pytest.raises(AuthenticationError, match="maximum token age"):
        provider.authenticate(AuthContext(f"Bearer {stale}"))

    future = _jwt(
        "secret-one",
        {
            "iss": "issuer",
            "aud": "aud",
            "sub": "alice",
            "iat": now + 10,
            "exp": now + 60,
        },
    )
    with pytest.raises(AuthenticationError, match="issued in the future"):
        provider.authenticate(AuthContext(f"Bearer {future}"))


def test_hs256_jwt_provider_requires_and_revokes_jti():
    now = time.time()
    provider = Hs256JwtAuthProvider(
        principal_kind="human",
        keys={"k1": "secret-one"},
        issuer="issuer",
        audience="aud",
        require_jti=True,
        revoked_jtis=frozenset({"revoked-123"}),
    )

    missing = _jwt(
        "secret-one",
        {
            "iss": "issuer",
            "aud": "aud",
            "sub": "alice",
            "exp": now + 60,
        },
    )
    with pytest.raises(AuthenticationError, match="jti is required"):
        provider.authenticate(AuthContext(f"Bearer {missing}"))

    revoked = _jwt(
        "secret-one",
        {
            "iss": "issuer",
            "aud": "aud",
            "sub": "alice",
            "exp": now + 60,
            "jti": "revoked-123",
        },
    )
    with pytest.raises(AuthenticationError, match="revoked"):
        provider.authenticate(AuthContext(f"Bearer {revoked}"))

    valid = _jwt(
        "secret-one",
        {
            "iss": "issuer",
            "aud": "aud",
            "sub": "alice",
            "exp": now + 60,
            "jti": "active-456",
        },
    )
    principal = provider.authenticate(AuthContext(f"Bearer {valid}"))
    assert principal.attributes["token_id_hash"] == hashlib.sha256(
        b"active-456"
    ).hexdigest()[:16]
    assert "active-456" not in principal.attributes.values()


def test_auth_provider_factory_loads_jwt_age_and_revocation_controls(monkeypatch):
    monkeypatch.setenv("HUMANQUEUE_HUMAN_AUTH_PROVIDER", "jwt-hs256")
    monkeypatch.setenv("HUMANQUEUE_HUMAN_JWT_KEYS", '{"k1":"secret-one"}')
    monkeypatch.setenv("HUMANQUEUE_HUMAN_JWT_ISSUER", "issuer")
    monkeypatch.setenv("HUMANQUEUE_HUMAN_JWT_AUDIENCE", "aud")
    monkeypatch.setenv("HUMANQUEUE_HUMAN_JWT_MAX_TOKEN_AGE_SECONDS", "45")
    monkeypatch.setenv("HUMANQUEUE_HUMAN_JWT_REQUIRE_JTI", "true")
    monkeypatch.setenv(
        "HUMANQUEUE_HUMAN_JWT_REVOKED_JTIS",
        '["revoked-a","revoked-b"]',
    )

    provider = load_auth_provider("human")
    assert isinstance(provider, Hs256JwtAuthProvider)
    assert provider.max_token_age_seconds == 45
    assert provider.require_jti is True
    assert provider.revoked_jtis == frozenset({"revoked-a", "revoked-b"})


def test_auth_provider_factory_rejects_invalid_revocation_shape(monkeypatch):
    monkeypatch.setenv("HUMANQUEUE_HUMAN_AUTH_PROVIDER", "jwt-hs256")
    monkeypatch.setenv("HUMANQUEUE_HUMAN_JWT_KEYS", '{"k1":"secret-one"}')
    monkeypatch.setenv("HUMANQUEUE_HUMAN_JWT_ISSUER", "issuer")
    monkeypatch.setenv("HUMANQUEUE_HUMAN_JWT_AUDIENCE", "aud")
    monkeypatch.setenv(
        "HUMANQUEUE_HUMAN_JWT_REVOKED_JTIS",
        '{"not":"a-list"}',
    )

    with pytest.raises(ValueError, match="JSON array"):
        load_auth_provider("human")
