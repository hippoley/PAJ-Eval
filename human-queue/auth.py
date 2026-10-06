"""Optional bearer-token binding for HumanQueue logical human actors."""

from __future__ import annotations

import json
import os
import secrets
from dataclasses import dataclass


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
