# Contributing

Thanks for helping improve fast-brain.

## Project Goal

fast-brain helps local agents keep durable memory outside the prompt and retrieve only the context needed for the current task.

Prefer small, boring changes that make memory safer, retrieval better, or context smaller.

## Development Setup

```bash
cp .env.example .env
docker compose up --build
```

API:

```txt
http://localhost:8088
```

Health check:

```bash
curl http://localhost:8088/health
```

## Before Opening A PR

Run the smallest useful check:

```bash
python3 -m compileall fast_brain plugins/fast-brain
```

If your change touches Docker or migrations, also run:

```bash
docker compose up --build
```

## Deployment Notes

- Changes under `fast_brain/`, `migrations/`, `Dockerfile`, `compose.yaml`, or API docs require redeploying the fast-brain Docker service.
- Changes under `plugins/fast-brain/` require updating every Hermes host/profile that has the plugin installed.
- Changes to Hermes environment variables require updating that Hermes host and restarting the Hermes process/session.
- Backend-only changes do not update already-installed Hermes plugins.

## Code Guidelines

- Keep changes small.
- Reuse existing functions before adding new ones.
- Do not add new services, workers, queues or dependencies unless needed for a proven problem.
- Keep migrations idempotent; existing deployments rerun `migrations/001_init.sql` on startup.
- Never silently drop or mark unprocessed messages as consolidated.
- Treat tool outputs as potentially large; avoid injecting them back into context unless needed.
- Do not commit secrets or real `.env` files.

## Memory Model

Use existing fields first:

- `agent_id` separates shared memory namespaces.
- `device_id` identifies the writer.
- `messages.metadata` stores runtime/tool details.
- `memories.metadata` stores lifecycle hints before adding columns.
- `consolidation_status` tracks message processing state.

## Useful Smoke Tests

Store a message:

```bash
curl -X POST "$FAST_BRAIN_URL/v1/messages" \
  -H "Authorization: Bearer $FAST_BRAIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"contrib-smoke","role":"user","content":"hello","agent_id":"hermes","metadata":{"source":"contrib"}}'
```

Read recent messages:

```bash
curl -H "Authorization: Bearer $FAST_BRAIN_API_KEY" \
  "$FAST_BRAIN_URL/v1/sessions/contrib-smoke/recent?limit=1"
```

Build recommended context:

```bash
curl -X POST "$FAST_BRAIN_URL/v1/context" \
  -H "Authorization: Bearer $FAST_BRAIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"hello","agent_id":"hermes","session_id":"contrib-smoke","max_chars":1000}'
```

## Roadmap

See `docs/plan.md`.
