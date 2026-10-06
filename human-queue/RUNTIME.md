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

Use two terminals from the repository root.

Terminal A:

```bash
python human-queue/demo_blocked_process.py producer
```

You should see:

```text
[agent] WAITING_FOR_HUMAN wait_...
```

The process remains blocked.

Terminal B:

```bash
python human-queue/demo_blocked_process.py human
```

Choose `approve`. Terminal A then continues by itself:

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

1. expose the same contract over HTTP/SSE
2. connect the web UI to the runtime instead of fixture data
3. add leases/claims for multiple human reviewers
4. add webhook/MCP/GitHub resume adapters
5. add audit signatures and policy provenance
6. replace polling with event delivery for distributed deployment

The architectural rule is simple: **UI is optional; the durable boundary is the
product primitive.**
