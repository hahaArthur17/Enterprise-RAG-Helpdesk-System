import asyncio
import logging
from datetime import datetime, timezone
from services.clients import supabase, embedding_model
from services.document_processor import process_pdf

logger = logging.getLogger("ai-service")


async def process_document_jobs():
    """Background task that polls for pending jobs and processes them."""
    while True:
        try:
            response = (
                supabase.table("document_jobs")
                .select("*")
                .eq("status", "pending")
                .order("created_at")
                .limit(5)
                .execute()
            )

            for job in response.data:
                job_id = job["id"]
                file_path = job["file_path"]
                logger.info(f"Processing job {job_id}: {job['filename']}")

                supabase.table("document_jobs").update(
                    {"status": "processing"}
                ).eq("id", job_id).execute()

                try:
                    chunks = process_pdf(file_path)
                    if not chunks:
                        raise ValueError("No readable text found in PDF.")

                    logger.info(f"Job {job_id}: {len(chunks)} chunks to embed.")
                    for chunk in chunks:
                        vector_embedding = embedding_model.encode(chunk).tolist()
                        supabase.table("documents").insert(
                            {"content": chunk, "embedding": vector_embedding}
                        ).execute()

                    supabase.table("document_jobs").update(
                        {
                            "status": "completed",
                            "chunks_count": len(chunks),
                            "completed_at": datetime.now(timezone.utc).isoformat(),
                        }
                    ).eq("id", job_id).execute()
                    logger.info(f"Job {job_id} completed: {len(chunks)} chunks stored.")

                except Exception as e:
                    logger.error(f"Job {job_id} failed: {str(e)}")
                    supabase.table("document_jobs").update(
                        {
                            "status": "failed",
                            "error_message": str(e),
                            "completed_at": datetime.now(timezone.utc).isoformat(),
                        }
                    ).eq("id", job_id).execute()

        except Exception as e:
            logger.error(f"Worker poll error: {str(e)}")

        await asyncio.sleep(5)
