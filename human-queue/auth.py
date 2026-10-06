"""Optional bearer-token binding for HumanQueue logical human actors."""

from __future__ import annotations

import json
import os
import secrets
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
    return set()
