# HumanQueue Runtime — executable E2E

The public page demonstrates the interaction model. This directory now also
contains a deliberately small **real blocking primitive**.

## The contract

```text
machine
  -> ask(...)
  -> durable WAITING_FOR_HUMAN
  -> human decides exactly once
  -> decision is persisted
  -> blocked machine observes it
  -> machine resumes
```

The first implementation is SQLite-backed and standard-library-only. It is not
intended to be the final distributed architecture; it is the smallest artifact
that proves HumanQueue is more than UI.

## Run the proof

Use the web UI plus a producer from the repository root.

Terminal A — start HumanQueue:\n\n```bash\npython human-queue/server.py\n```\n\nOpen `http://127.0.0.1:8765`. The header should switch to **durable runtime connected**.\n\nTerminal B — start a blocked producer:\n\n```bash\npython human-queue/demo_blocked_process.py producer\n```\n\nYou should see:

```text
[agent] WAITING_FOR_HUMAN wait_...
```

The process remains blocked.

The task appears automatically in the browser. Click **Approve**. Terminal B then continues by itself:

```text
[agent] RESUMED cleanup-step-3
[agent] deleting keys ... done
[agent] WORKFLOW_COMPLETE
```

That transition is the current Reality Delta.

## Semantics already enforced

- durable SQLite wait records
- idempotent producer submission via `idempotency_key`
- exactly-once decision boundary
- same-decision replay is safe
- conflicting second decisions fail loudly
- explicit `resume_token`
- blocking wait with timeout
- pending queue retrieval

## Next hardening steps

1. replace browser polling with SSE or event delivery\n2. add leases/claims for multiple human reviewers\n3. add webhook/MCP/GitHub resume adapters\n4. add audit signatures and policy provenance\n5. add authentication and actor identity\n6. move from single-node SQLite to an optional distributed store

The architectural rule is simple: **UI is optional; the durable boundary is the
product primitive.**
