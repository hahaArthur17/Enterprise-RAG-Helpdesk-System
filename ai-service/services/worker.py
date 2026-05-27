import asyncio
import logging
from datetime import datetime, timezone
from services.clients import supabase, embedding_model
from services.document_processor import process_pdf
from services.chunker import split_parent_child

logger = logging.getLogger("ai-service")


def _batch_embed(texts: list[str]) -> list[list[float]]:
    """Embed multiple texts in one call. SentenceTransformer handles batching internally."""
    if not texts:
        return []
    embeddings = embedding_model.encode(texts).tolist()
    return embeddings


def _ingest_chunks(
    chunks: list[dict],
    source_filename: str,
    job_id: str,
) -> int:
    """
    Insert parent-child chunks into Supabase.
    Uses batch embedding for all child chunks at once.
    """
    total_children = 0

    for chunk in chunks:
        # 1. Insert parent document
        parent_result = (
            supabase.table("parent_documents")
            .insert(
                {
                    "content": chunk["parent_content"],
                    "source_filename": chunk["source_filename"],
                    "section_title": chunk["section_title"],
                    "page_start": chunk["page_number"],
                    "page_end": chunk["page_number"],
                    "job_id": job_id,
                }
            )
            .execute()
        )
        parent_id = parent_result.data[0]["id"]

        # 2. Batch embed all children at once
        child_texts = [child["content"] for child in chunk["children"]]
        embeddings = _batch_embed(child_texts)

        # 3. Insert each child with pre-computed embedding
        for child, embedding in zip(chunk["children"], embeddings):
            supabase.table("documents").insert(
                {
                    "content": child["content"],
                    "embedding": embedding,
                    "parent_id": parent_id,
                    "page_number": child["page_number"],
                    "chunk_index": child["chunk_index"],
                    "source_filename": chunk["source_filename"],
                    "section_title": chunk["section_title"],
                }
            ).execute()
            total_children += 1

    return total_children


def _ingest_table_chunks(
    table_texts: list[str],
    source_filename: str,
    page_number: int,
    job_id: str,
) -> int:
    """
    Insert table chunks as standalone parent documents.
    Batch embeds all table texts at once.
    """
    if not table_texts:
        return 0

    # Batch embed all table texts
    embeddings = _batch_embed(table_texts)

    for table_text, embedding in zip(table_texts, embeddings):
        # Insert as parent
        parent_result = (
            supabase.table("parent_documents")
            .insert(
                {
                    "content": table_text,
                    "source_filename": source_filename,
                    "section_title": f"Table (page {page_number})",
                    "page_start": page_number,
                    "page_end": page_number,
                    "job_id": job_id,
                }
            )
            .execute()
        )
        parent_id = parent_result.data[0]["id"]

        # Insert one child record for vector search
        supabase.table("documents").insert(
            {
                "content": table_text,
                "embedding": embedding,
                "parent_id": parent_id,
                "page_number": page_number,
                "chunk_index": 0,
                "source_filename": source_filename,
                "section_title": f"Table (page {page_number})",
            }
        ).execute()

    return len(table_texts)


def _process_single_page(
    page: dict,
    filename: str,
    job_id: str,
) -> int:
    """Process one page: tables + text. Returns chunk count."""
    page_num = page["page_number"]
    chunks_inserted = 0

    # Table chunks (kept whole)
    if page["table_texts"]:
        chunks_inserted += _ingest_table_chunks(
            page["table_texts"], filename, page_num, job_id
        )

    # Text chunks via parent-child splitting
    if page["text"].strip():
        parent_child = split_parent_child(
            page["text"], filename, section_title=None, page_number=page_num
        )
        chunks_inserted += _ingest_chunks(parent_child, filename, job_id)

    return chunks_inserted


async def _process_job(job: dict):
    """Process a single document job."""
    job_id = job["id"]
    file_path = job["file_path"]
    filename = job["filename"]
    logger.info(f"Processing job {job_id}: {filename}")

    supabase.table("document_jobs").update(
        {"status": "processing"}
    ).eq("id", job_id).execute()

    try:
        # Step 1: Parse PDF (CPU-bound, run in thread pool)
        pages = await asyncio.to_thread(process_pdf, file_path, filename)
        if not pages:
            raise ValueError("No readable text found in PDF.")

        # Step 2: Process all pages concurrently
        # Each page is independent, so we can parallelize
        page_tasks = [
            asyncio.to_thread(_process_single_page, page, filename, job_id)
            for page in pages
        ]
        page_results = await asyncio.gather(*page_tasks)
        total_chunks = sum(page_results)

        # Step 3: Mark job as completed
        supabase.table("document_jobs").update(
            {
                "status": "completed",
                "chunks_count": total_chunks,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", job_id).execute()
        logger.info(f"Job {job_id} completed: {total_chunks} child chunks stored.")

    except Exception as e:
        logger.error(f"Job {job_id} failed: {str(e)}")
        supabase.table("document_jobs").update(
            {
                "status": "failed",
                "error_message": str(e),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", job_id).execute()


async def process_document_jobs():
    """Background task: poll for pending jobs and process them concurrently."""
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

            if response.data:
                # Process multiple jobs concurrently
                job_tasks = [_process_job(job) for job in response.data]
                await asyncio.gather(*job_tasks)

        except Exception as e:
            logger.error(f"Worker poll error: {str(e)}")

        await asyncio.sleep(5)
