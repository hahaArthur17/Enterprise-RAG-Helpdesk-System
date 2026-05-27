import sys
import time
import asyncio
import logging
from fastapi import FastAPI, Request
from routers import ask, ingest, upload
from services.worker import process_document_jobs

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("ai-service")

# --- App ---
app = FastAPI(title="Enterprise RAG AI Service")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(
        f"Path: {request.url.path} | Method: {request.method} "
        f"| Status: {response.status_code} | Time: {process_time:.4f}s"
    )
    return response


# --- Routers ---
app.include_router(ask.router)
app.include_router(ingest.router)
app.include_router(upload.router)


@app.get("/health")
async def health_check():
    return {"status": "Healthy", "service": "ai-service-with-groq-supabase"}


@app.on_event("startup")
async def start_background_worker():
    asyncio.create_task(process_document_jobs())
    logger.info("Background document processing worker started.")
