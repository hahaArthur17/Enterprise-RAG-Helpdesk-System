# Enterprise AI Helpdesk

An enterprise-ready AI helpdesk platform built with a decoupled full-stack architecture. The system uses Retrieval-Augmented Generation (RAG) to answer user questions from internal documents, provide source citations, and stream responses in real time.

The project is designed to demonstrate a production-oriented AI application architecture, combining a React frontend, an ASP.NET Core backend-for-frontend, a Python AI microservice, Groq-powered LLM inference, and Supabase pgvector for semantic search.

## Key Features

- RAG-based question answering over uploaded documents
- PDF, Markdown, and plain text document ingestion
- Recursive text chunking to preserve semantic context
- Vector similarity search with Supabase PostgreSQL and pgvector
- Groq LPU inference with Llama 3 for low-latency responses
- Streaming chat responses for a real-time typewriter experience
- Source citations linked to the retrieved document fragments
- Enterprise-focused API layer for authentication, rate limiting, audit logging, and service orchestration
- Fully containerized local development with Docker Compose

## Architecture Overview

```text
User
  |
  v
React Frontend
  |
  v
ASP.NET Core BFF / Backend API
  |
  v
Python FastAPI AI Microservice
  |
  +--> Groq API / Llama 3
  |
  +--> Supabase PostgreSQL + pgvector
```

## Tech Stack

| Layer | Technologies |
|---|---|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Backend API / BFF | ASP.NET Core 8, C#, `IHttpClientFactory`, structured logging |
| AI Microservice | Python 3.10+, FastAPI, LangChain |
| LLM Inference | Groq LPU, Llama 3 |
| Vector Database | Supabase, PostgreSQL, pgvector |
| DevOps | Docker, Docker Compose |

## Technical Decisions

| Component | Choice | Engineering Rationale |
|---|---|---|
| Inference Engine | Groq API | Groq's LPU technology provides very low-latency inference, which is important for helpdesk workflows where users expect fast responses. |
| Vector Storage | Supabase pgvector | Supabase combines managed PostgreSQL with vector search, allowing relational business data and embeddings to be stored in one platform. |
| Service Decoupling | .NET and Python | ASP.NET Core handles enterprise API concerns such as authentication, rate limiting, audit logging, and orchestration, while Python provides access to mature AI and ML tooling. |
| Backend Pattern | BFF / Microservices | The BFF isolates frontend-facing API concerns from the AI microservice, allowing the AI layer to scale and evolve independently. |
| Resilience | Polly policies in .NET | Retry and circuit breaker policies help the backend handle transient AI service failures and timeout scenarios gracefully. |

## RAG Pipeline

### 1. Document Ingestion

The ingestion pipeline supports PDF, Markdown, and plain text files. Documents are parsed, normalized, and split into smaller semantic chunks using recursive character text splitting.

### 2. Embedding and Storage

Each document chunk is converted into a high-dimensional embedding and stored in Supabase PostgreSQL with pgvector. Metadata is stored alongside each chunk to support traceability and source citation.

### 3. Retrieval

When a user asks a question, the AI service performs a cosine similarity search against the vector database to retrieve the most relevant document fragments.

### 4. Grounded Generation

Retrieved context is injected into a controlled system prompt before calling the LLM. This helps the assistant generate answers that are grounded in the available knowledge base instead of relying only on model memory.

### 5. Streaming and Citation

The generated answer is streamed back to the frontend in real time. The response includes references to the source fragments used to generate the answer.

## Local Development

The system is containerized with Docker Compose for consistent local development across environments.

### Prerequisites

- Docker
- Docker Compose
- Groq API key
- Supabase project URL
- Supabase API key

### Environment Configuration

Create environment configuration files for each service.

For the AI service:

```env
GROQ_API_KEY=your_groq_api_key
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_api_key
```

For the .NET backend, configure database connection strings and service settings in:

```text
backend-dotnet/.../appsettings.json
```

### Run the Full Stack

From the root directory, run:

```bash
docker-compose up --build
```

### Service URLs

| Service | URL |
|---|---|
| Frontend | `http://localhost:5173` |
| Backend API Swagger | `http://localhost:5263/swagger` |
| AI Service Docs | `http://localhost:8000/docs` |

## Challenges and Solutions

### Latency Optimization

The project uses Groq LPU inference to reduce Time to First Token compared with traditional cloud-hosted LLM inference providers. This improves the perceived responsiveness of the helpdesk experience.

### Environment Consistency

Docker multi-stage builds are used to manage the Python AI service footprint while keeping the .NET and frontend environments reproducible across machines.

### Service Reliability

The .NET backend uses resilient HTTP policies, including retry and circuit breaker patterns, to handle transient AI service timeouts and prevent cascading failures.

## Roadmap

- [ ] Hybrid search combining BM25 keyword search with semantic search
- [ ] Chat persistence using Redis or PostgreSQL
- [ ] Role-based access control for enterprise knowledge bases
- [ ] Admin dashboard for document ingestion and index management
- [ ] Deployment migration path to Azure Container Apps

## Project Purpose

This project was built as a portfolio-grade full-stack AI application to demonstrate practical experience with modern frontend engineering, enterprise backend architecture, microservice design, and retrieval-augmented generation.
