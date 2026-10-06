"""Optional bearer-token binding for HumanQueue logical human actors."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class AuthContext:
    authorization: str | None
    headers: dict[str, str] = field(default_factory=dict)
    client: str | None = None


@dataclass(frozen=True)
class Principal:
    actor: str
    kind: str
    provider: str
    attributes: dict[str, Any] = field(default_factory=dict)


class AuthProvider(Protocol):
    def authenticate(
        self,
        context: AuthContext,
        *,
        claimed_actor: str | None = None,
    ) -> Principal:
        ...


class AuthenticationError(RuntimeError):
    pass


class ActorMismatchError(AuthenticationError):
    pass


@dataclass(frozen=True)
class ActorAuthenticator:
    """Bind bearer tokens to actor names without persisting credentials."""

    actor_tokens: dict[str, str]

    def __post_init__(self) -> None:
        cleaned: dict[str, str] = {}
        seen_tokens: set[str] = set()
        for actor, token in self.actor_tokens.items():
            actor = str(actor).strip()
            token = str(token).strip()
            if not actor or not token:
                raise ValueError("actor names and tokens must be non-empty")
            if token in seen_tokens:
                raise ValueError("actor tokens must be unique")
            cleaned[actor] = token
            seen_tokens.add(token)
        object.__setattr__(self, "actor_tokens", cleaned)

    @classmethod
    def from_env(
        cls,
        env_var: str = "HUMANQUEUE_ACTOR_TOKENS",
    ) -> "ActorAuthenticator | None":
        raw = os.environ.get(env_var)
        if not raw:
            return None
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{env_var} must contain a JSON object") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{env_var} must contain a JSON object")
        return cls({str(actor): str(token) for actor, token in value.items()})

    def authenticate(
        self,
        authorization: str | None,
        *,
        claimed_actor: str | None = None,
    ) -> str:
        if not authorization or not authorization.startswith("Bearer "):
            raise AuthenticationError("bearer token required")
        supplied = authorization[len("Bearer ") :].strip()
        if not supplied:
            raise AuthenticationError("bearer token required")

        resolved = None
        for actor, token in self.actor_tokens.items():
            if secrets.compare_digest(supplied, token):
                resolved = actor
                break
        if resolved is None:
            raise AuthenticationError("invalid bearer token")

        claimed = (claimed_actor or "").strip()
        if claimed and claimed != resolved:
            raise ActorMismatchError(
                f"claimed actor {claimed!r} does not match authenticated actor"
            )
        return resolved


def ensure_disjoint_authenticators(
    human: ActorAuthenticator | None,
    machine: ActorAuthenticator | None,
) -> None:
    """Reject credentials shared across human and machine trust domains."""
    if human is None or machine is None:
        return
    overlap = set(human.actor_tokens.values()) & set(machine.actor_tokens.values())
    if overlap:
        raise ValueError(
            "human and machine token domains must not share credentials"
        )


@dataclass(frozen=True)
class BearerTokenAuthProvider:
    """Adapt the local token map to the generic Principal/AuthProvider contract."""

    authenticator: ActorAuthenticator
    principal_kind: str
    provider_name: str = "bearer-token"

    @classmethod
    def from_env(
        cls,
        env_var: str,
        *,
        principal_kind: str,
        provider_name: str = "bearer-token",
    ) -> "BearerTokenAuthProvider | None":
        authenticator = ActorAuthenticator.from_env(env_var)
        if authenticator is None:
            return None
        return cls(
            authenticator=authenticator,
            principal_kind=principal_kind,
            provider_name=provider_name,
        )

    def authenticate(
        self,
        context: AuthContext,
        *,
        claimed_actor: str | None = None,
    ) -> Principal:
        actor = self.authenticator.authenticate(
            context.authorization,
            claimed_actor=claimed_actor,
        )
        return Principal(
            actor=actor,
            kind=self.principal_kind,
            provider=self.provider_name,
        )


def adapt_authenticator(
    authenticator: ActorAuthenticator | None,
    *,
    principal_kind: str,
) -> BearerTokenAuthProvider | None:
    if authenticator is None:
        return None
    return BearerTokenAuthProvider(
        authenticator=authenticator,
        principal_kind=principal_kind,
    )


def ensure_disjoint_providers(
    human: AuthProvider | None,
    machine: AuthProvider | None,
) -> None:
    """Enforce credential separation for built-in local providers."""
    if _local_provider_secrets(human) & _local_provider_secrets(machine):
        raise ValueError(
            "human and machine auth providers must not share credentials"
        )


@dataclass(frozen=True)
class TrustedHeaderAuthProvider:
    """Accept an actor asserted by a trusted gateway/proxy.

    A separate proof header prevents clients from simply spoofing the actor
    header when the HumanQueue server is reachable directly.
    """

    principal_kind: str
    proof_secret: str
    actor_header: str = "X-HumanQueue-Actor"
    proof_header: str = "X-HumanQueue-Proxy-Secret"
    provider_name: str = "trusted-header"

    def __post_init__(self) -> None:
        if not self.principal_kind.strip():
            raise ValueError("principal_kind is required")
        if not self.proof_secret:
            raise ValueError("trusted-header proof_secret is required")
        if not self.actor_header.strip() or not self.proof_header.strip():
            raise ValueError("trusted-header names must be non-empty")

    def authenticate(
        self,
        context: AuthContext,
        *,
        claimed_actor: str | None = None,
    ) -> Principal:
        supplied_proof = context.headers.get(self.proof_header)
        if not supplied_proof or not secrets.compare_digest(
            supplied_proof,
            self.proof_secret,
        ):
            raise AuthenticationError("trusted proxy proof required")

        actor = str(context.headers.get(self.actor_header) or "").strip()
        if not actor:
            raise AuthenticationError("trusted actor header required")

        claimed = (claimed_actor or "").strip()
        if claimed and claimed != actor:
            raise ActorMismatchError(
                f"claimed actor {claimed!r} does not match authenticated actor"
            )

        return Principal(
            actor=actor,
            kind=self.principal_kind,
            provider=self.provider_name,
        )


def load_auth_provider(
    principal_kind: str,
) -> AuthProvider | None:
    """Load an auth provider for human or machine principals from env.

    Backward compatibility:
    - no explicit provider mode + legacy token env => bearer-token
    - no configured credentials => auth disabled
    """
    if principal_kind not in {"human", "machine"}:
        raise ValueError("principal_kind must be human or machine")

    prefix = "HUMANQUEUE_HUMAN" if principal_kind == "human" else "HUMANQUEUE_MACHINE"
    legacy_token_env = (
        "HUMANQUEUE_ACTOR_TOKENS"
        if principal_kind == "human"
        else "HUMANQUEUE_MACHINE_TOKENS"
    )
    mode = os.environ.get(f"{prefix}_AUTH_PROVIDER", "").strip().lower()

    if not mode:
        if os.environ.get(legacy_token_env):
            mode = "bearer"
        elif os.environ.get(f"{prefix}_PROXY_SECRET"):
            mode = "trusted-header"
        else:
            return None

    if mode in {"bearer", "bearer-token"}:
        provider = BearerTokenAuthProvider.from_env(
            legacy_token_env,
            principal_kind=principal_kind,
        )
        if provider is None:
            raise ValueError(
                f"{legacy_token_env} is required for bearer auth"
            )
        return provider

    if mode in {"jwt", "jwt-hs256"}:
        raw_keys = os.environ.get(f"{prefix}_JWT_KEYS", "")
        if not raw_keys:
            raise ValueError(f"{prefix}_JWT_KEYS is required for jwt-hs256 auth")
        try:
            keys = json.loads(raw_keys)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{prefix}_JWT_KEYS must contain a JSON object") from exc
        if not isinstance(keys, dict):
            raise ValueError(f"{prefix}_JWT_KEYS must contain a JSON object")
        issuer = os.environ.get(f"{prefix}_JWT_ISSUER", "")
        audience = os.environ.get(f"{prefix}_JWT_AUDIENCE", "")
        actor_claim = os.environ.get(f"{prefix}_JWT_ACTOR_CLAIM", "sub")
        leeway = float(os.environ.get(f"{prefix}_JWT_LEEWAY_SECONDS", "30"))
        max_age_raw = os.environ.get(f"{prefix}_JWT_MAX_TOKEN_AGE_SECONDS", "").strip()
        max_age = float(max_age_raw) if max_age_raw else None
        require_jti = os.environ.get(
            f"{prefix}_JWT_REQUIRE_JTI",
            "",
        ).strip().lower() in {"1", "true", "yes", "on"}
        revoked_raw = os.environ.get(f"{prefix}_JWT_REVOKED_JTIS", "").strip()
        if revoked_raw:
            try:
                revoked_value = json.loads(revoked_raw)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{prefix}_JWT_REVOKED_JTIS must contain a JSON array"
                ) from exc
            if not isinstance(revoked_value, list):
                raise ValueError(
                    f"{prefix}_JWT_REVOKED_JTIS must contain a JSON array"
                )
            revoked_jtis = frozenset(str(value) for value in revoked_value)
        else:
            revoked_jtis = frozenset()
        return Hs256JwtAuthProvider(
            principal_kind=principal_kind,
            keys={str(k): str(v) for k, v in keys.items()},
            issuer=issuer,
            audience=audience,
            actor_claim=actor_claim,
            leeway_seconds=leeway,
            max_token_age_seconds=max_age,
            require_jti=require_jti,
            revoked_jtis=revoked_jtis,
        )

    if mode == "trusted-header":
        proof_secret = os.environ.get(f"{prefix}_PROXY_SECRET", "")
        actor_header = os.environ.get(
            f"{prefix}_ACTOR_HEADER",
            (
                "X-HumanQueue-Human"
                if principal_kind == "human"
                else "X-HumanQueue-Machine"
            ),
        )
        proof_header = os.environ.get(
            f"{prefix}_PROXY_PROOF_HEADER",
            "X-HumanQueue-Proxy-Secret",
        )
        return TrustedHeaderAuthProvider(
            principal_kind=principal_kind,
            proof_secret=proof_secret,
            actor_header=actor_header,
            proof_header=proof_header,
        )

    raise ValueError(f"unsupported auth provider: {mode}")


def _local_provider_secrets(provider: AuthProvider | None) -> set[str]:
    if isinstance(provider, BearerTokenAuthProvider):
        return set(provider.authenticator.actor_tokens.values())
    if isinstance(provider, TrustedHeaderAuthProvider):
        return {provider.proof_secret}
    if isinstance(provider, Hs256JwtAuthProvider):
        return set(provider.keys.values())
    return set()


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    try:
        return base64.urlsafe_b64decode(segment + padding)
    except Exception as exc:
        raise AuthenticationError("invalid JWT encoding") from exc


@dataclass(frozen=True)
class Hs256JwtAuthProvider:
    """Validate compact HS256 JWTs using stdlib-only cryptography.

    This is signed JWT support, not full OIDC/JWKS support.
    """

    principal_kind: str
    keys: dict[str, str]
    issuer: str
    audience: str
    actor_claim: str = "sub"
    leeway_seconds: float = 30.0
    max_token_age_seconds: float | None = None
    require_jti: bool = False
    revoked_jtis: frozenset[str] = frozenset()
    provider_name: str = "jwt-hs256"

    def __post_init__(self) -> None:
        cleaned = {
            str(kid).strip(): str(secret).strip()
            for kid, secret in self.keys.items()
            if str(kid).strip() and str(secret).strip()
        }
        if not cleaned:
            raise ValueError("JWT keys are required")
        if not self.issuer.strip():
            raise ValueError("JWT issuer is required")
        if not self.audience.strip():
            raise ValueError("JWT audience is required")
        if not self.actor_claim.strip():
            raise ValueError("JWT actor_claim is required")
        if self.leeway_seconds < 0:
            raise ValueError("JWT leeway_seconds must be >= 0")
        if self.max_token_age_seconds is not None and self.max_token_age_seconds <= 0:
            raise ValueError("JWT max_token_age_seconds must be > 0")
        object.__setattr__(self, "keys", cleaned)
        object.__setattr__(
            self,
            "revoked_jtis",
            frozenset(str(value) for value in self.revoked_jtis if str(value)),
        )

    def authenticate(
        self,
        context: AuthContext,
        *,
        claimed_actor: str | None = None,
    ) -> Principal:
        authorization = context.authorization or ""
        if not authorization.startswith("Bearer "):
            raise AuthenticationError("JWT bearer token required")
        token = authorization[len("Bearer ") :].strip()
        parts = token.split(".")
        if len(parts) != 3:
            raise AuthenticationError("invalid JWT format")

        header_segment, payload_segment, signature_segment = parts
        try:
            header = json.loads(_b64url_decode(header_segment))
            claims = json.loads(_b64url_decode(payload_segment))
        except json.JSONDecodeError as exc:
            raise AuthenticationError("invalid JWT JSON") from exc
        if not isinstance(header, dict) or not isinstance(claims, dict):
            raise AuthenticationError("invalid JWT structure")
        if header.get("alg") != "HS256":
            raise AuthenticationError("JWT alg must be HS256")

        kid = str(header.get("kid") or "").strip()
        if not kid:
            if len(self.keys) != 1:
                raise AuthenticationError("JWT kid is required")
            kid = next(iter(self.keys))
        secret = self.keys.get(kid)
        if secret is None:
            raise AuthenticationError("unknown JWT kid")

        signed = f"{header_segment}.{payload_segment}".encode()
        expected = hmac.new(
            secret.encode(),
            signed,
            hashlib.sha256,
        ).digest()
        actual = _b64url_decode(signature_segment)
        if not hmac.compare_digest(expected, actual):
            raise AuthenticationError("invalid JWT signature")

        if claims.get("iss") != self.issuer:
            raise AuthenticationError("invalid JWT issuer")
        audience = claims.get("aud")
        if isinstance(audience, str):
            audiences = {audience}
        elif isinstance(audience, list):
            audiences = {str(value) for value in audience}
        else:
            audiences = set()
        if self.audience not in audiences:
            raise AuthenticationError("invalid JWT audience")

        now = time.time()
        leeway = float(self.leeway_seconds)
        exp = claims.get("exp")
        if exp is None:
            raise AuthenticationError("JWT exp is required")
        try:
            exp_value = float(exp)
        except (TypeError, ValueError) as exc:
            raise AuthenticationError("invalid JWT exp") from exc
        if now > exp_value + leeway:
            raise AuthenticationError("JWT expired")

        nbf = claims.get("nbf")
        if nbf is not None:
            try:
                nbf_value = float(nbf)
            except (TypeError, ValueError) as exc:
                raise AuthenticationError("invalid JWT nbf") from exc
            if now + leeway < nbf_value:
                raise AuthenticationError("JWT not yet valid")

        iat = claims.get("iat")
        if self.max_token_age_seconds is not None:
            if iat is None:
                raise AuthenticationError("JWT iat is required")
            try:
                iat_value = float(iat)
            except (TypeError, ValueError) as exc:
                raise AuthenticationError("invalid JWT iat") from exc
            if iat_value > now + leeway:
                raise AuthenticationError("JWT issued in the future")
            if now - iat_value > self.max_token_age_seconds + leeway:
                raise AuthenticationError("JWT exceeds maximum token age")

        jti = str(claims.get("jti") or "").strip()
        if self.require_jti and not jti:
            raise AuthenticationError("JWT jti is required")
        if jti and jti in self.revoked_jtis:
            raise AuthenticationError("JWT has been revoked")
        token_id_hash = (
            hashlib.sha256(jti.encode()).hexdigest()[:16]
            if jti
            else None
        )

        actor = str(claims.get(self.actor_claim) or "").strip()
        if not actor:
            raise AuthenticationError(
                f"JWT actor claim {self.actor_claim!r} is required"
            )
        claimed = (claimed_actor or "").strip()
        if claimed and claimed != actor:
            raise ActorMismatchError(
                f"claimed actor {claimed!r} does not match authenticated actor"
            )

        attributes = {
            "issuer": self.issuer,
            "audience": self.audience,
            "kid": kid,
        }
        if token_id_hash is not None:
            attributes["token_id_hash"] = token_id_hash

        return Principal(
            actor=actor,
            kind=self.principal_kind,
            provider=self.provider_name,
            attributes=attributes,
        )
