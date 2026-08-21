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
- Hermes plugin stores minimal message metadata and skips empty assistant turns.
- Safe block-based consolidation with per-message `consolidation_status`.
- Search threshold through `min_score`.
- Memory access tracking with `access_count` and `last_accessed_at`.
- Near-duplicate consolidated memories are skipped before insert.
- Recent memories can be reviewed through `/v1/memories/recent`.
- Basic context recommendation endpoint: `POST /v1/context`.
- Public endpoint configured through `https://fb-memory.osviel.duckdns.org`.
- Manual compaction through `/v1/compact` and per-session consolidation endpoints.
- Safe external automatic compaction through `scripts/compact-once.sh`.

## Phase 1: Reliable Memory

Purpose: make storage and consolidation safe enough to trust.

Deliverables:

- Verify Hermes writes full turns including tool messages.
- Add a direct smoke command or script for memory provider checks.
- Inspect failed consolidation messages with `/v1/consolidate/failed`.
- Retry failed messages with `/v1/consolidate/session/{session_id}/retry-failed`.
- Skip oversized failed tool outputs with `/v1/consolidate/session/{session_id}/skip-failed`.
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
- Keep insert-time deduplication for consolidated memories.
- Add memory importance field only if real use shows the need.
- Add manual memory correction workflow if bad memories appear.

Acceptance checks:

- `/v1/search` returns zero results for unrelated queries.
- Relevant memories are recalled across different Hermes profiles sharing `agent_id`.
- Repeated useful memories show increased `access_count`.

## Phase 3: Context Engine V1

Purpose: make `/v1/context` the preferred context source for agents.

Plugin deployment note: any change under `plugins/fast-brain/` must be copied or redeployed to every Hermes host/profile using that plugin. Backend redeploy alone is not enough.

Deliverables:

- Hermes plugin `prefetch` uses `/v1/context` with fallback to `/v1/search`.
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

Manual flow first:

1. Check `/v1/stats`.
2. Check `/v1/consolidate/pending`.
3. Run `/v1/compact` with a conservative `max_sessions` and `min_age_minutes=60` or higher.
4. Check `/v1/consolidate/failed`.
5. Review `/v1/memories/recent`.
6. Delete obsolete/noisy memories.
7. Retry failed sessions only after choosing a larger `max_chars` or accepting that oversized tool outputs need separate handling.
8. Skip failed oversized tool outputs when their raw content is not worth durable memory.

Deliverables:

- Detect sessions with high pending message volume.
- Skip active sessions by default using `min_age_minutes`.
- Compact old tool outputs into concise summaries.
- Preserve current task, decisions, constraints and recent exchanges.
- Add configurable retention for raw messages after safe consolidation.
- Run automatic compaction externally with `scripts/compact-once.sh` once manual reports are stable.

Acceptance checks:

- Long sessions can be compacted without losing decisions.
- Raw messages are retained until safely consolidated.
- Context size does not grow without bound.
- Automatic compaction does not run until manual compaction is proven safe.
- Automatic compaction must never process sessions that are still active.

Automatic flow:

1. Schedule `scripts/compact-once.sh` every 30-60 minutes.
2. Keep `FAST_BRAIN_COMPACT_MIN_AGE_MINUTES=60` or higher.
3. Keep `FAST_BRAIN_COMPACT_MAX_SESSIONS` small.
4. Review `/v1/consolidate/failed` and `/v1/memories/recent` after the first runs.

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
3. Run manual `/v1/compact` against real Hermes sessions.
4. Review `/v1/consolidate/failed` after compaction.
5. Decide whether Hermes `prefetch` should switch from `/v1/search` to `/v1/context`.
