-- Session ledger schema for agentic infrastructure engineering platform
-- Tracks all agent sessions, approval requests, and audit events

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- Agent sessions
CREATE TABLE IF NOT EXISTS sessions (
    session_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id        TEXT NOT NULL,
    tenant_id       TEXT NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at        TIMESTAMPTZ,
    token_usage     INT NOT NULL DEFAULT 0,
    approval_status TEXT NOT NULL DEFAULT 'not_required'
                    CHECK (approval_status IN ('not_required', 'pending', 'approved', 'rejected')),
    metadata        JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS sessions_tenant_idx ON sessions (tenant_id);
CREATE INDEX IF NOT EXISTS sessions_agent_idx ON sessions (agent_id);
CREATE INDEX IF NOT EXISTS sessions_started_at_idx ON sessions (started_at DESC);

-- T2 approval requests
CREATE TABLE IF NOT EXISTS approval_requests (
    request_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id      UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
    pr_url          TEXT,
    pr_number       INT,
    requested_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decided_at      TIMESTAMPTZ,
    decision        TEXT CHECK (decision IN ('approved', 'rejected', 'pending')),
    decided_by      TEXT,
    metadata        JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS approval_requests_session_idx ON approval_requests (session_id);

-- Audit log
CREATE TABLE IF NOT EXISTS audit_log (
    id              BIGSERIAL PRIMARY KEY,
    event_type      TEXT NOT NULL,
    session_id      UUID,
    tenant_id       TEXT NOT NULL,
    user_id         TEXT,
    event_data      JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS audit_log_tenant_idx ON audit_log (tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS audit_log_event_type_idx ON audit_log (event_type);

-- Idempotency keys
CREATE TABLE IF NOT EXISTS idempotency_keys (
    idempotency_key TEXT PRIMARY KEY,
    result_json     JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '24 hours'
);

CREATE INDEX IF NOT EXISTS idempotency_keys_expires_idx ON idempotency_keys (expires_at);

-- Episodic memory
CREATE TABLE IF NOT EXISTS episodic_memory (
    id          BIGSERIAL PRIMARY KEY,
    agent_id    TEXT NOT NULL,
    event_type  TEXT NOT NULL,
    content     JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS episodic_memory_agent_idx ON episodic_memory (agent_id, event_type);

-- IaC documents for vector search
CREATE TABLE IF NOT EXISTS iac_documents (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chunk_id    TEXT UNIQUE NOT NULL,
    content     TEXT NOT NULL,
    metadata    JSONB NOT NULL DEFAULT '{}',
    embedding   vector(1024),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS iac_documents_embedding_idx
    ON iac_documents USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS iac_documents_metadata_idx
    ON iac_documents USING GIN (metadata);
