CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL DEFAULT 'hermes',
    device_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS messages (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    consolidation_status TEXT NOT NULL DEFAULT 'pending' CHECK (consolidation_status IN ('pending', 'processing', 'consolidated', 'failed')),
    consolidated_at TIMESTAMPTZ,
    consolidation_memory_id BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE messages ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}';
ALTER TABLE messages ADD COLUMN IF NOT EXISTS consolidation_status TEXT NOT NULL DEFAULT 'pending';
ALTER TABLE messages ADD COLUMN IF NOT EXISTS consolidated_at TIMESTAMPTZ;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS consolidation_memory_id BIGINT;

UPDATE messages SET consolidation_status = 'consolidated' WHERE consolidated_at IS NOT NULL;

CREATE TABLE IF NOT EXISTS memories (
    id BIGSERIAL PRIMARY KEY,
    agent_id TEXT NOT NULL DEFAULT 'hermes',
    session_id TEXT REFERENCES sessions(id) ON DELETE SET NULL,
    kind TEXT NOT NULL DEFAULT 'fact',
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    embedding vector(__EMBEDDING_DIMENSIONS__) NOT NULL,
    access_count INTEGER NOT NULL DEFAULT 0,
    last_accessed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE memories ADD COLUMN IF NOT EXISTS access_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE memories ADD COLUMN IF NOT EXISTS last_accessed_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS memories_embedding_idx
ON memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS memories_agent_idx ON memories(agent_id);
CREATE INDEX IF NOT EXISTS messages_session_idx ON messages(session_id, id);
DROP INDEX IF EXISTS messages_unconsolidated_idx;
CREATE INDEX IF NOT EXISTS messages_unconsolidated_idx ON messages(session_id, id) WHERE consolidation_status = 'pending';
