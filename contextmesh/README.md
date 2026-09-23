# ContextMesh Web

Public product surface for ContextMesh.

## Live pages

- Workspace: https://hippoley.github.io/PAJ-Eval/contextmesh/
- Admin: https://hippoley.github.io/PAJ-Eval/contextmesh/admin.html
- API / deployment: https://hippoley.github.io/PAJ-Eval/contextmesh/api.html

## Files

```
contextmesh/
├── index.html      # Context Studio / Workspace
├── admin.html      # Runtime control plane
├── api.html        # API and deployment contract
├── style.css       # Shared UI system
├── demo.js         # Browser-side demo runtime
└── README.md
```

## Current deployment mode

GitHub Pages hosts the static UI. The Workspace includes a browser-side demo runtime so the product flow can be experienced without a backend.

The production ContextMesh runtime is a separate service. Point the UI at the FastAPI backend to enable:

- heterogeneous file ingestion
- resumable / durable ingest jobs
- addressable ContextBlocks
- full-coverage evaluation
- SSE job progress
- provider-specific model routing
- retry / cancel / resume
- score-preservation benchmarks
- vLLM / LMCache telemetry

## Runtime contract

ContextMesh uses retrieval and ranking only to schedule reading order.

```
ranking = scheduling, not filtering
```

A final score is not valid until ingest, semantic-readiness and execution coverage gates pass.

## Production topology

```
Browser / Web UI
      |
      v
ContextMesh API
      |
      +-- object storage (S3 / MinIO)
      +-- durable workers / queue
      +-- ContextBlock catalog
      +-- provider adapters
      |    +-- OpenAI
      |    +-- Anthropic
      |    +-- Gemini
      |    +-- Qwen / DashScope
      |    +-- vLLM / SGLang
      +-- LMCache / model telemetry
```
