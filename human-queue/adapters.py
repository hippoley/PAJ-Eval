"""Resume adapters for HumanQueue.

Adapters deliver a committed human decision to the system that originally
paused. Delivery is distinct from execution acknowledgement: the target system
still reports PROCESS_RESUMED / PROCESS_COMPLETED back to HumanQueue.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
import time
from typing import Protocol
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

from runtime import HumanQueue, Wait


def sanitize_target(url: str) -> str:
    """Remove credentials, query strings and fragments from audit provenance."""
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError("webhook URL must use http or https")
    host = parts.hostname
    if parts.port:
        host = f"{host}:{parts.port}"
    return urlunsplit((parts.scheme, host, parts.path or "/", "", ""))


class ResumeAdapter(Protocol):
    name: str

    def dispatch(self, queue: HumanQueue, item: Wait) -> dict:
        ...


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay: float = 0.25
    multiplier: float = 2.0
    max_delay: float = 5.0

    def delay_for(self, attempt: int) -> float:
        if attempt < 1:
            raise ValueError("attempt must be >= 1")
        return min(self.base_delay * (self.multiplier ** (attempt - 1)), self.max_delay)


def dispatch_with_retry(
    queue: HumanQueue,
    item: Wait,
    adapter: ResumeAdapter,
    *,
    policy: RetryPolicy | None = None,
    sleeper=time.sleep,
) -> dict:
    policy = policy or RetryPolicy()
    if policy.max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    target = getattr(adapter, "audit_target", adapter.name)
    last_error: Exception | None = None

    for attempt in range(1, policy.max_attempts + 1):
        queue.record_resume_delivery_event(
            item.id,
            event_type="RESUME_DELIVERY_ATTEMPT",
            actor=adapter.name,
            adapter=adapter.name,
            target=target,
            attempt=attempt,
        )
        try:
            return adapter.dispatch(queue, queue.get(item.id))
        except Exception as exc:
            last_error = exc
            if attempt >= policy.max_attempts:
                queue.record_resume_delivery_event(
                    item.id,
                    event_type="RESUME_DEAD_LETTERED",
                    actor=adapter.name,
                    adapter=adapter.name,
                    target=target,
                    attempt=attempt,
                    error=f"{type(exc).__name__}: {exc}",
                )
                break
            delay = policy.delay_for(attempt)
            queue.record_resume_delivery_event(
                item.id,
                event_type="RESUME_DELIVERY_FAILED",
                actor=adapter.name,
                adapter=adapter.name,
                target=target,
                attempt=attempt,
                error=f"{type(exc).__name__}: {exc}",
                next_delay=delay,
            )
            sleeper(delay)

    assert last_error is not None
    raise last_error


class GenericWebhookAdapter:
    name = "webhook"

    def __init__(
        self,
        url: str,
        *,
        bearer_token: str | None = None,
        timeout: float = 5.0,
    ) -> None:
        self.url = url
        self.audit_target = sanitize_target(url)
        self.bearer_token = bearer_token
        self.timeout = timeout

    def dispatch(self, queue: HumanQueue, item: Wait) -> dict:
        """POST the committed decision to the paused system.

        A successful HTTP response means only "resume request delivered".
        It does not mean the machine resumed; the target must acknowledge that
        separately through HumanQueue's machine acknowledgement protocol.
        """
        if item.execution_state not in {
            "resume_requested",
            "resumed",
            "completed",
            "failed",
        }:
            raise RuntimeError(f"{item.id} has no resume request")

        body = {
            "wait_id": item.id,
            "uri": item.uri,
            "source": item.source,
            "resume_token": item.resume_token,
            "decision": item.decision,
            "execution_state": item.execution_state,
        }
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "HumanQueue/0.1",
        }
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"

        request = Request(
            self.url,
            data=json.dumps(body, separators=(",", ":")).encode(),
            headers=headers,
            method="POST",
        )
        with urlopen(request, timeout=self.timeout) as response:
            raw = response.read()
            if response.status < 200 or response.status >= 300:
                raise RuntimeError(f"webhook returned HTTP {response.status}")

        queue.mark_resume_dispatched(
            item.id,
            actor=self.name,
            adapter=self.name,
            target=self.audit_target,
        )
        return {
            "status": response.status,
            "target": self.audit_target,
            "body": raw.decode(errors="replace"),
        }


class GitHubRepositoryDispatchAdapter:
    """Resume a GitHub workflow through repository_dispatch."""

    name = "github_repository_dispatch"

    def __init__(
        self,
        repository: str,
        *,
        token: str,
        event_type: str = "humanqueue-resume",
        api_base: str = "https://api.github.com",
        timeout: float = 5.0,
    ) -> None:
        if "/" not in repository or repository.startswith("/") or repository.endswith("/"):
            raise ValueError("repository must be in owner/name form")
        self.repository = repository
        self.token = token
        self.event_type = event_type
        self.timeout = timeout
        self.url = (
            api_base.rstrip("/")
            + f"/repos/{repository}/dispatches"
        )
        self.audit_target = f"github://{repository}/{event_type}"

    def dispatch(self, queue: HumanQueue, item: Wait) -> dict:
        if item.execution_state not in {
            "resume_requested",
            "resumed",
            "completed",
            "failed",
        }:
            raise RuntimeError(f"{item.id} has no resume request")

        payload = {
            "event_type": self.event_type,
            "client_payload": {
                "wait_id": item.id,
                "uri": item.uri,
                "source": item.source,
                "resume_token": item.resume_token,
                "decision": item.decision,
            },
        }
        request = Request(
            self.url,
            data=json.dumps(payload, separators=(",", ":")).encode(),
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "User-Agent": "HumanQueue/0.1",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            method="POST",
        )
        with urlopen(request, timeout=self.timeout) as response:
            raw = response.read()
            if response.status < 200 or response.status >= 300:
                raise RuntimeError(f"GitHub returned HTTP {response.status}")

        queue.mark_resume_dispatched(
            item.id,
            actor=self.name,
            adapter=self.name,
            target=self.audit_target,
        )
        return {
            "status": response.status,
            "repository": self.repository,
            "event_type": self.event_type,
            "body": raw.decode(errors="replace"),
        }
