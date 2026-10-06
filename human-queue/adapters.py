"""Resume adapters for HumanQueue.

Adapters deliver a committed human decision to the system that originally
paused. Delivery is distinct from execution acknowledgement: the target system
still reports PROCESS_RESUMED / PROCESS_COMPLETED back to HumanQueue.
"""

from __future__ import annotations

import json
from dataclasses import asdict
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
