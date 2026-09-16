# Deployment configuration

PAJ-Eval is an open instrument, not a single shared backend.

Each deployment owns its own:

- Supabase project
- database
- Edge Function / ingestion endpoint
- publishable client key
- server-side service role secret
- treatment assignment configuration
- researcher access policy

A fork MUST NOT send events to the canonical research database unless its operator intentionally configures that endpoint.

## What may be public

A Supabase **publishable key** is designed to be embedded in public clients. Treat it as an identifier with restricted public capability, not as an administrative secret. Public capability must be constrained by Row Level Security and/or a narrow ingestion Edge Function.

The project URL and ingestion function URL may also be public.

## What must never enter the repository or browser

- `SUPABASE_SERVICE_ROLE_KEY`
- database password / direct connection string with credentials
- researcher/admin tokens
- signing secrets
- private webhook secrets

Store these only in the managed deployment secret store (for example Supabase Edge Function secrets or GitHub Actions Secrets when needed server-side). They must never be emitted into static GitHub Pages JavaScript.

## Repository pattern

Committed:

- `.env.example`
- schema / migrations
- API contracts
- example deployment configuration with placeholders

Ignored:

- `.env`
- `.env.*`
- `config.local.yml`
- `config.local.yaml`
- `secrets.yml`
- `secrets.yaml`

If YAML is preferred locally, use `config.local.yaml` and keep it ignored. Do not put real credentials in a committed YAML file.

## Canonical public research deployment

The official public Probe Player may point to Jialun's research ingestion endpoint. That is a deployment choice, not a library default.

The source default remains `local` / no remote persistence. A deployer must opt in by supplying its own backend configuration.

Conceptually:

```text
upstream PAJ-Eval repo
       |
       +-- canonical public deployment -> Jialun's Supabase project
       |
       +-- researcher A fork ----------> researcher A's Supabase project
       |
       +-- researcher B local ----------> no network / local trace only
```

## Trigger / ingestion isolation

Any scheduled trigger, webhook, Edge Function, or evaluation worker is deployment-scoped. The canonical deployment invokes canonical infrastructure. A fork invokes the fork owner's configured infrastructure. No personal trigger identifier or secret is hard-coded into the shared source tree.
