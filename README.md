# fast-brain

External semantic memory for Hermes agents.

## What It Does

- Stores conversation messages by session.
- Stores consolidated memories with embeddings.
- Searches memories semantically through PostgreSQL + pgvector.
- Uses any OpenAI-compatible embeddings endpoint.
- Runs as a Docker/Portainer stack.

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
```

`EMBEDDINGS_BASE_URL` must be the API root, not the full `/embeddings` URL.

## Endpoints

```txt
GET  /health
POST /v1/messages
GET  /v1/sessions/{session_id}/recent
POST /v1/memories
POST /v1/search
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

The first integration target should be a Hermes memory provider plugin. MCP can be added later if other agents need the same memory.

Skipped: custom migration framework and full consolidation worker. Add them when the API shape is proven with Hermes.
