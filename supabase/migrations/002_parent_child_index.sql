-- =============================================
-- Migration: Parent-Child Document Indexing
-- =============================================
-- Run this AFTER 001_init_schema.sql
-- Safe to run on existing data: old rows get NULL parent_id

-- 1. Parent documents table (large chunks, no vectors)
CREATE TABLE IF NOT EXISTS parent_documents (
    id              BIGSERIAL PRIMARY KEY,
    content         TEXT NOT NULL,
    source_filename TEXT,
    section_title   TEXT,
    page_start      INT,
    page_end        INT,
    job_id          UUID REFERENCES document_jobs(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. Add metadata columns to documents (child chunks)
ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS parent_id        BIGINT REFERENCES parent_documents(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS page_number      INT,
    ADD COLUMN IF NOT EXISTS chunk_index      INT,
    ADD COLUMN IF NOT EXISTS source_filename  TEXT,
    ADD COLUMN IF NOT EXISTS section_title    TEXT;

-- 3. Index for fast parent lookups
CREATE INDEX IF NOT EXISTS idx_documents_parent_id ON documents(parent_id);

-- 4. Rewrite match_documents: return parent content when available
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding  vector(384),
    match_threshold  float,
    match_count      int
)
RETURNS TABLE (
    id              bigint,
    content         text,
    child_content   text,
    similarity      float,
    source_filename text,
    section_title   text,
    page_number     int,
    parent_id       bigint
)
LANGUAGE sql STABLE
AS $$
    SELECT
        d.id,
        COALESCE(p.content, d.content) AS content,
        d.content                       AS child_content,
        1 - (d.embedding <=> query_embedding) AS similarity,
        COALESCE(d.source_filename, p.source_filename),
        COALESCE(d.section_title,   p.section_title),
        d.page_number,
        d.parent_id
    FROM documents d
    LEFT JOIN parent_documents p ON p.id = d.parent_id
    WHERE 1 - (d.embedding <=> query_embedding) > match_threshold
    ORDER BY d.embedding <=> query_embedding
    LIMIT match_count;
$$;
