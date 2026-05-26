-- =============================================
-- Enterprise RAG Helpdesk System - Full Schema
-- =============================================

-- 1. Enable the pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================
-- 2. Documents table (RAG knowledge base)
-- =============================================
CREATE TABLE documents (
    id BIGSERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding VECTOR(384)  -- 'all-MiniLM-L6-v2' output dimension
);

-- Similarity search function for RAG queries
CREATE OR REPLACE FUNCTION match_documents (
    query_embedding vector(384),
    match_threshold float,
    match_count int
)
RETURNS TABLE (
    id bigint,
    content text,
    similarity float
)
LANGUAGE sql STABLE
AS $$
    SELECT
        documents.id,
        documents.content,
        1 - (documents.embedding <=> query_embedding) AS similarity
    FROM documents
    WHERE 1 - (documents.embedding <=> query_embedding) > match_threshold
    ORDER BY documents.embedding <=> query_embedding
    LIMIT match_count;
$$;

-- =============================================
-- 3. Chat messages table
-- =============================================
CREATE TABLE chat_messages (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- =============================================
-- 4. Document processing jobs table (async queue)
-- =============================================
CREATE TABLE document_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    file_path TEXT NOT NULL,
    chunks_count INT,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

-- Index for the background worker to quickly find pending jobs
CREATE INDEX IF NOT EXISTS idx_document_jobs_status ON document_jobs (status) WHERE status = 'pending';
