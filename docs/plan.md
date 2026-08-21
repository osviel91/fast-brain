# fast-brain Project Plan

## Direction

fast-brain is evolving from external semantic memory for Hermes into a local agent memory and context layer.

The goal is simple: keep long-term memory outside the prompt, and send agents only the context needed for the current task.

```txt
Agent Runtime
  -> fast-brain context layer
    -> working context
    -> long-term memory
    -> retrieval
    -> safe consolidation
```

## Current Baseline

Implemented:

- Persistent sessions, messages and memories in PostgreSQL + pgvector.
- Hermes memory provider plugin.
- Automatic memory prefetch through `/v1/search`.
- Explicit tools: `fb_search_memory`, `fb_remember`, `fb_forget`.
- Full message metadata capture when Hermes provides runtime messages.
- Safe block-based consolidation with per-message `consolidation_status`.
- Search threshold through `min_score`.
- Memory access tracking with `access_count` and `last_accessed_at`.
- Basic context recommendation endpoint: `POST /v1/context`.
- Public endpoint configured through `https://fb-memory.osviel.duckdns.org`.

## Phase 1: Reliable Memory

Purpose: make storage and consolidation safe enough to trust.

Deliverables:

- Verify Hermes writes full turns including tool messages.
- Add a direct smoke command or script for memory provider checks.
- Add a way to inspect failed consolidation messages.
- Add a retry path for `consolidation_status = 'failed'`.
- Avoid duplicate message storage across Hermes restarts if possible.

Acceptance checks:

- A Hermes turn increases `messages` count.
- Tool results are stored with metadata.
- Consolidation never marks unprocessed messages as consolidated.
- Oversized messages are visible as failed, not silently lost.

## Phase 2: Better Retrieval

Purpose: return useful memories, not just nearest vectors.

Deliverables:

- Tune default `min_score` with real Hermes sessions.
- Add recency and usage signals to ranking.
- Add simple deduplication before returning search results.
- Add memory importance field only if real use shows the need.
- Add manual memory correction workflow if bad memories appear.

Acceptance checks:

- `/v1/search` returns zero results for unrelated queries.
- Relevant memories are recalled across different Hermes profiles sharing `agent_id`.
- Repeated useful memories show increased `access_count`.

## Phase 3: Context Engine V1

Purpose: make `/v1/context` the preferred context source for agents.

Deliverables:

- Update Hermes plugin `prefetch` to optionally use `/v1/context`.
- Include recent messages plus retrieved memories in one compact block.
- Add character budget configuration through env vars.
- Skip oversized tool outputs by default.
- Add one small integration smoke test against the remote endpoint.

Acceptance checks:

- Hermes receives relevant memories and recent context from one endpoint.
- Context response stays under configured budget.
- Large old tool outputs are not injected back into prompt.

## Phase 4: Memory Lifecycle

Purpose: separate temporary work from durable knowledge.

Deliverables:

- Define memory classes: `working`, `episodic`, `semantic`.
- Store lifecycle metadata in existing `metadata` first.
- Promote repeated/important episodic memories into semantic memories.
- Expire or archive stale working memories.
- Add lightweight stats for memory kinds and age.

Acceptance checks:

- Temporary task state does not pollute long-term recall.
- Durable user/project facts survive across sessions.
- Old working memories can be listed and cleaned.

## Phase 5: Context Compaction

Purpose: reduce runtime context growth during long sessions.

Deliverables:

- Detect sessions with high pending message volume.
- Compact old tool outputs into concise summaries.
- Preserve current task, decisions, constraints and recent exchanges.
- Add configurable retention for raw messages after safe consolidation.

Acceptance checks:

- Long sessions can be compacted without losing decisions.
- Raw messages are retained until safely consolidated.
- Context size does not grow without bound.

## Phase 6: Agent-Agnostic Layer

Purpose: make fast-brain useful beyond Hermes.

Deliverables:

- Document a generic HTTP integration contract.
- Keep Hermes plugin as one client, not the core design.
- Add examples for local agents using `/v1/messages`, `/v1/search`, `/v1/context`.
- Add agent namespace guidance using `agent_id` and `device_id`.

Acceptance checks:

- Another local agent can write messages and request context without Hermes code.
- Shared memory works by using the same `agent_id`.
- Isolated memory works by using different `agent_id` values.

## Deferred On Purpose

Not now:

- Background workers.
- Queue systems.
- New databases.
- Full tokenizers.
- Complex ranking frameworks.
- Automatic deletion of raw history.

Add these only when the simple HTTP/API flow is proven insufficient.

## Next Session Checklist

1. Run a Hermes local memory smoke test through the FQDN.
2. Confirm full message capture with at least one tool call.
3. Add failed-consolidation inspection endpoint.
4. Add retry endpoint for failed messages.
5. Decide whether Hermes `prefetch` should switch from `/v1/search` to `/v1/context`.
