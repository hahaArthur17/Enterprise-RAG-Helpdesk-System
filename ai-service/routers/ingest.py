import asyncio
import logging
from fastapi import APIRouter, HTTPException
from models.schemas import IngestRequest, IngestResponse
from services.clients import embedding_model, supabase

logger = logging.getLogger("ai-service")
router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest_knowledge(request: IngestRequest):
    """Embed plain text and store in Supabase vector database."""
    logger.info("Received text for ingestion.")
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    try:
        # CPU-bound embedding, offload to thread pool
        vector_embedding = await asyncio.to_thread(
            embedding_model.encode, request.text
        )
        vector_embedding = vector_embedding.tolist()

        # I/O-bound Supabase insert, offload to thread pool
        data, count = await asyncio.to_thread(
            lambda: supabase.table("documents")
            .insert({"content": request.text, "embedding": vector_embedding})
            .execute()
        )
        inserted_id = data[1][0]["id"]
        logger.info(f"Successfully stored document with ID: {inserted_id}")
        return IngestResponse(
            message="Successfully embedded and stored in vector database.",
            document_id=inserted_id,
        )
    except Exception as e:
        logger.error(f"Error during ingestion process: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to embed and store data.")
