# fast-brain

External semantic memory for Hermes agents.

## What It Does

- Stores conversation messages by session.
- Stores full agent messages when the runtime provides them, including tool metadata.
- Stores consolidated memories with embeddings.
- Searches memories semantically through PostgreSQL + pgvector.
- Builds a small recommended context block for agents that want it.
- Uses any OpenAI-compatible embeddings endpoint.
- Runs as a Docker/Portainer stack.

## Architecture

```txt
Hermes
  -> fast-brain Hermes memory provider plugin
    -> fast-brain HTTP API
      -> OpenAI-compatible embeddings endpoint
      -> PostgreSQL + pgvector
```

The plugin is installed into each Hermes profile. The API is shared and runs in Portainer. PostgreSQL stores both relational data and vector embeddings, so there is only one database to back up and operate.

## Memory Flow

```txt
User asks Hermes something
  -> plugin calls /v1/search with the user query
  -> fast-brain returns only relevant memories
  -> Hermes receives those memories as extra context
  -> Hermes answers
  -> plugin stores the completed user/assistant turn in /v1/messages
```

Hermes can also explicitly use tools exposed by the plugin:

```txt
fb_search_memory  -> semantic recall
fb_remember       -> store durable fact
fb_forget         -> delete wrong/obsolete memory by id
```

## What Is Stored

```txt
sessions   -> conversation/session identity
messages   -> raw user/assistant/tool turns
memories   -> durable facts, decisions, preferences, project notes
embedding  -> semantic vector for each memory
metadata   -> tool calls/results and runtime fields attached to messages
agent_id   -> memory namespace
device_id  -> Hermes instance/profile that wrote the turn
```

Use the same `FAST_BRAIN_AGENT_ID` across Hermes instances to share memory. Use different `FAST_BRAIN_DEVICE_ID` values to identify where a turn came from.

## Growth And Cleanup

There are two growth paths:

- `messages` grows with every completed turn.
- `memories` grows only when Hermes calls `fb_remember` or when consolidation creates durable memories.

Current cleanup:

- `fb_forget` / `DELETE /v1/memories/{id}` deletes a known bad memory.
- Raw database deletion or volume reset is still the only full cleanup path.

Recommended retention model:

```txt
raw messages
  -> keep short/medium term
  -> consolidate into memories
  -> delete or archive after 30-90 days

durable memories
  -> keep long term
  -> delete only if wrong, obsolete, duplicate, or explicitly requested
```

## How Hermes Knows When To Use Memory

There are two mechanisms:

- Automatic prefetch: before each turn, the provider searches fast-brain using the current user query and injects relevant memories.
- Explicit tools: Hermes sees `fb_search_memory`, `fb_remember`, and `fb_forget` in its tool schema and can call them when useful.

The plugin system prompt tells Hermes that fast-brain is active and should be used for durable recall. This keeps the active prompt small: only matching memories are injected, not the whole memory store.

## Compacting For Small Models

The goal is to help self-hosted models with around 64k context avoid repeated full-context compression. fast-brain should become the long-term semantic layer, while Hermes keeps only the immediate working set in prompt.

Plan:

1. Keep recent turns in Hermes/session context for natural conversation.
2. Store every completed turn in `messages` for audit and later consolidation.
3. Periodically consolidate old messages into short `memories`.
4. Search only `memories` before each turn.
5. Inject only the top few relevant memories into Hermes.
6. Delete or archive raw messages after they are safely consolidated.

Consolidation should produce compact items like:

```txt
preference: User prefers concise, direct engineering answers.
project: User is building fast-brain, an external semantic memory for Hermes.
decision: fast-brain uses PostgreSQL + pgvector and OpenAI-compatible embeddings.
task: Add memory lifecycle management and compaction policy.
```

Compaction endpoints:

```txt
POST /v1/consolidate/session/{session_id}
POST /v1/consolidate/session/{session_id}/retry-failed
POST /v1/consolidate/session/{session_id}/skip-failed
POST /v1/compact
GET  /v1/stats
GET  /v1/consolidate/pending
GET  /v1/consolidate/failed
```

Current consolidation uses an OpenAI-compatible summarizer when `SUMMARIZER_BASE_URL` and `SUMMARIZER_MODEL` are configured. Consolidation now claims only the pending message block that fits in `max_chars`, then marks only those message IDs as consolidated. Oversized single messages are marked `failed` instead of being silently truncated and treated as processed.

If the summarizer is not configured or fails, fast-brain falls back to extractive consolidation for the claimed block only.

Context selection endpoint:

```txt
POST /v1/context
```

It returns relevant memories plus recent session messages within a simple character budget. This is intentionally a recommendation layer first; full prompt pruning still depends on Hermes exposing a context-construction hook.

Summarizer config example:

```env
SUMMARIZER_BASE_URL=http://host.docker.internal:11434/v1
SUMMARIZER_API_KEY=local
SUMMARIZER_MODEL=qwen2.5:7b
```

Expected memory kinds:

```txt
project, decision, preference, task, fact, correction, summary
```

Manual compaction flow:

```bash
curl -H "Authorization: Bearer $FAST_BRAIN_API_KEY" \
  "$FAST_BRAIN_URL/v1/stats?agent_id=hermes"

curl -H "Authorization: Bearer $FAST_BRAIN_API_KEY" \
  "$FAST_BRAIN_URL/v1/consolidate/pending?agent_id=hermes"

curl -X POST -H "Authorization: Bearer $FAST_BRAIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"hermes","kind":"summary","max_chars":3000}' \
  "$FAST_BRAIN_URL/v1/consolidate/session/<session_id>"

curl -X POST -H "Authorization: Bearer $FAST_BRAIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"hermes","kind":"summary","max_chars":3000,"max_sessions":10}' \
  "$FAST_BRAIN_URL/v1/compact"

curl -H "Authorization: Bearer $FAST_BRAIN_API_KEY" \
  "$FAST_BRAIN_URL/v1/consolidate/failed?agent_id=hermes"

curl -X POST -H "Authorization: Bearer $FAST_BRAIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"hermes","kind":"summary","max_chars":12000}' \
  "$FAST_BRAIN_URL/v1/consolidate/session/<session_id>/retry-failed"

curl -X POST -H "Authorization: Bearer $FAST_BRAIN_API_KEY" \
  "$FAST_BRAIN_URL/v1/consolidate/session/<session_id>/skip-failed"
```

Run manual compaction first. Add automatic compaction only after the pending/failed reports are boring and predictable.

The lazy rule: do not summarize everything all the time. Keep raw messages cheap, consolidate only inactive/old sessions, and inject only memories that semantic search says are relevant.

## Stack

- FastAPI
- PostgreSQL 16 + pgvector
- Remote OpenAI-compatible embeddings
- Docker Compose / Portainer

## Local Run

```bash
cp .env.example .env
docker compose up --build
```

API: `http://localhost:8088`

## Environment

```env
FAST_BRAIN_API_KEY=change-me
DATABASE_URL=postgresql://fastbrain:fastbrain@postgres:5432/fastbrain
EMBEDDINGS_BASE_URL=https://api.openai.com/v1
EMBEDDINGS_API_KEY=change-me
EMBEDDINGS_MODEL=text-embedding-3-small
EMBEDDINGS_DIMENSIONS=1536
SUMMARIZER_BASE_URL=
SUMMARIZER_API_KEY=
SUMMARIZER_MODEL=
```

`EMBEDDINGS_BASE_URL` must be the API root, not the full `/embeddings` URL.

For local testing without a remote embedding model:

```env
EMBEDDINGS_BASE_URL=mock://local
EMBEDDINGS_API_KEY=local
EMBEDDINGS_MODEL=mock
```

## Endpoints

```txt
GET  /health
GET  /v1/stats?agent_id=hermes
GET  /v1/config
POST /v1/summarizer/test
POST /v1/messages
GET  /v1/sessions/{session_id}/recent
POST /v1/memories
DELETE /v1/memories/{id}?agent_id=hermes
POST /v1/search
POST /v1/context
GET  /v1/consolidate/pending?agent_id=hermes
GET  /v1/consolidate/failed?agent_id=hermes
POST /v1/consolidate/session/{session_id}
POST /v1/consolidate/session/{session_id}/retry-failed
POST /v1/consolidate/session/{session_id}/skip-failed
POST /v1/compact
POST /v1/consolidate
```

Authenticated endpoints expect:

```txt
Authorization: Bearer $FAST_BRAIN_API_KEY
```

## Portainer

1. Push this repo to GitHub.
2. GitHub Actions publishes `ghcr.io/<owner>/fast-brain:latest` on pushes to `main`.
3. In Portainer, create a Stack from Git or paste `compose.yaml`.
4. Set the environment variables from `.env.example`.

## Hermes Integration

Install the Hermes memory provider plugin into each Hermes profile:

```bash
mkdir -p ~/.hermes/plugins
cp -R plugins/fast-brain ~/.hermes/plugins/fast-brain
```

Configure `~/.hermes/.env`:

```env
FAST_BRAIN_URL=http://192.168.31.144:4668
FAST_BRAIN_API_KEY=change-me
FAST_BRAIN_AGENT_ID=hermes
FAST_BRAIN_DEVICE_ID=macbook
```

Enable it:

```bash
hermes config set memory.provider fast-brain
hermes memory status
```

For multiple Hermes instances, use the same `FAST_BRAIN_AGENT_ID` to share memory. Use different `FAST_BRAIN_DEVICE_ID` values to identify each instance. Use different `FAST_BRAIN_AGENT_ID` values only when you want isolated memories.

Skipped: custom migration framework and full consolidation worker. Add them when the API shape is proven with Hermes.
