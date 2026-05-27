# Enterprise RAG Helpdesk System

An enterprise-ready AI helpdesk platform that uses Retrieval-Augmented Generation (RAG) to answer user questions from uploaded documents. Built with a decoupled microservice architecture: React frontend, ASP.NET Core backend (BFF), and a Python FastAPI AI service.

## Architecture

```
User (Browser)
    |
    v
React Frontend (Vite + TypeScript)
    |
    v
ASP.NET Core BFF  ──→  PostgreSQL (chat_messages)
    |
    v
Python FastAPI AI Service
    ├── Groq API (Llama 3 LLM)
    └── Supabase PostgreSQL + pgvector (documents, document_jobs)
```

## Key Features

- **Async PDF Processing** — Upload returns immediately (HTTP 202); a background worker handles parsing, chunking, embedding, and storage
- **Enhanced PDF Pipeline** — pdfplumber for table extraction, OCR support for scanned pages (Tesseract), regex-based text cleaning
- **RAG Question Answering** — Vector similarity search via pgvector, context-augmented LLM generation via Groq
- **Job Status Polling** — Frontend polls for processing status: `pending` -> `processing` -> `completed` / `failed`
- **JWT Authentication** — .NET backend handles auth; all API calls require Bearer token
- **Docker Compose** — Full stack containerized for local development

## Tech Stack

| Layer | Technologies |
|---|---|
| Frontend | React 19, TypeScript, Vite |
| Backend API (BFF) | ASP.NET Core (.NET 10), C#, Npgsql, JWT Bearer |
| AI Microservice | Python 3.10+, FastAPI, Uvicorn |
| PDF Processing | pdfplumber, pytesseract (OCR), LangChain text splitters |
| Embeddings | Sentence-Transformers (all-MiniLM-L6-v2, 384-dim) |
| LLM Inference | Groq API, Llama 3.1 8B Instant |
| Vector Database | Supabase PostgreSQL + pgvector |
| DevOps | Docker, Docker Compose |

## Project Structure

```
Enterprise-RAG-Helpdesk-System/
├── frontend/                    # React SPA
│   └── src/App.tsx              # Single-file app (login, chat, upload)
├── backend-dotnet/              # ASP.NET Core BFF
│   └── BackendApi/Controllers/
│       ├── AuthController.cs    # JWT login
│       ├── ChatController.cs    # Chat -> AI service proxy
│       └── DocumentController.cs# Upload -> AI service, status proxy
├── ai-service/                  # Python FastAPI AI microservice
│   ├── main.py                  # App entry point (middleware, routers, startup)
│   ├── config.py                # Environment variables
│   ├── models/
│   │   └── schemas.py           # Pydantic request/response models
│   ├── routers/
│   │   ├── ask.py               # POST /ask — RAG pipeline
│   │   ├── ingest.py            # POST /ingest — text embedding
│   │   └── upload.py            # POST /upload, GET /jobs/{id}
│   ├── services/
│   │   ├── clients.py           # Groq, Supabase, embedding model init
│   │   ├── document_processor.py# PDF parsing, table extraction, OCR, cleaning
│   │   ├── rag.py               # RAG pipeline logic
│   │   └── worker.py            # Background job processor
│   ├── Dockerfile
│   └── requirements.txt
├── supabase/migrations/
│   └── 001_init_schema.sql      # Full database schema
└── docker-compose.yml
```

## AI Service Module Design

| Module | Responsibility |
|---|---|
| `config.py` | Load environment variables (GROQ_API_KEY, SUPABASE_URL, SUPABASE_KEY) |
| `models/schemas.py` | Pydantic models for all API request/response types |
| `services/clients.py` | Initialize external clients (Groq, Supabase, SentenceTransformer) |
| `services/document_processor.py` | PDF pipeline: pdfplumber parsing, table-to-sentence conversion, OCR fallback, text cleaning, chunking |
| `services/rag.py` | RAG pipeline: embed question -> vector search -> build prompt -> LLM generation |
| `services/worker.py` | Background worker: polls `document_jobs` table, processes pending PDFs |
| `routers/ask.py` | `POST /ask` — RAG question answering |
| `routers/ingest.py` | `POST /ingest` — direct text embedding |
| `routers/upload.py` | `POST /upload` (202 async), `GET /jobs/{id}` (status polling) |
| `main.py` | FastAPI app init, middleware, router registration, startup hook |

## Async Processing Flow

```
1. User uploads PDF
2. POST /upload -> save file -> insert job (status=pending) -> return 202 + job_id
3. Frontend polls GET /jobs/{job_id} every 3 seconds
4. Background worker picks up pending job -> status=processing
5. Worker: pdfplumber parse -> table extraction -> OCR check -> text clean -> chunk -> embed -> store
6. Worker: status=completed (or failed with error_message)
7. Frontend sees "completed" -> stops polling
```

## Database Schema (Supabase)

```sql
-- Vector knowledge base
CREATE TABLE documents (
    id BIGSERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding VECTOR(384)
);

-- Async processing queue
CREATE TABLE document_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    file_path TEXT NOT NULL,
    chunks_count INT,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

-- Chat history
CREATE TABLE chat_messages (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);
```

Full schema with vector search function: `supabase/migrations/001_init_schema.sql`

## API Endpoints

| Method | Path | Service | Description |
|---|---|---|---|
| POST | `/api/auth/login` | .NET | JWT login |
| POST | `/api/chat` | .NET -> Python | Chat with RAG |
| POST | `/api/document/upload` | .NET -> Python | Upload PDF (returns 202) |
| GET | `/api/document/status/{jobId}` | .NET -> Python | Poll job status |
| POST | `/ask` | Python | RAG question answering |
| POST | `/ingest` | Python | Embed and store text |
| POST | `/upload` | Python | Accept PDF, create job |
| GET | `/jobs/{job_id}` | Python | Job status |
| GET | `/health` | Python | Health check |

## Local Development

### Prerequisites

- Docker and Docker Compose
- Groq API key
- Supabase project (URL + API key)

### Environment Files

`ai-service/.env`:
```env
GROQ_API_KEY=your_groq_api_key
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_api_key
```

`backend-dotnet/BackendApi/.env`:
```env
SUPABASE_DB_CONNECTION=your_postgres_connection_string
JWT_SECRET_KEY=your_jwt_secret
```

### Run

```bash
docker-compose up --build
```

### Service URLs

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend Swagger | http://localhost:5263/swagger |
| AI Service Docs | http://localhost:8000/docs |

## Roadmap

- [ ] WebSocket push notifications for job completion (replace polling)
- [ ] Hybrid search (BM25 + semantic)
- [ ] Role-based access control
- [ ] Admin dashboard for document management
- [ ] Azure Container Apps deployment
