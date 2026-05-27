import asyncio
import logging
from datetime import datetime, timezone
from services.clients import supabase, embedding_model
from services.document_processor import process_pdf
from services.chunker import split_parent_child

logger = logging.getLogger("ai-service")


def _ingest_chunks(
    chunks: list[dict],
    source_filename: str,
    job_id: str,
) -> int:
    """
    Insert parent-child chunks into Supabase.

    For each parent chunk:
      1. Insert into parent_documents -> get parent_id
      2. For each child: embed and insert into documents with parent_id

    Returns total number of child chunks stored.
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

        # 2. Embed and insert each child chunk
        for child in chunk["children"]:
            vector_embedding = embedding_model.encode(child["content"]).tolist()
            supabase.table("documents").insert(
                {
                    "content": child["content"],
                    "embedding": vector_embedding,
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
    Tables are kept whole (not split into children) to preserve structure.
    """
    for table_text in table_texts:
        embedding = embedding_model.encode(table_text).tolist()

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

        # Insert one child record (content = parent) for vector search
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
                filename = job["filename"]
                logger.info(f"Processing job {job_id}: {filename}")

                supabase.table("document_jobs").update(
                    {"status": "processing"}
                ).eq("id", job_id).execute()

                try:
                    # Step 1: Parse PDF into structured page data
                    pages = process_pdf(file_path, filename)
                    if not pages:
                        raise ValueError("No readable text found in PDF.")

                    total_chunks = 0

                    # Step 2: Process each page
                    for page in pages:
                        page_num = page["page_number"]

                        # Ingest table chunks (kept whole, no child splitting)
                        if page["table_texts"]:
                            total_chunks += _ingest_table_chunks(
                                page["table_texts"],
                                filename,
                                page_num,
                                job_id,
                            )

                        # Ingest text chunks via parent-child splitting
                        if page["text"].strip():
                            parent_child = split_parent_child(
                                page["text"],
                                filename,
                                section_title=None,
                                page_number=page_num,
                            )
                            total_chunks += _ingest_chunks(
                                parent_child,
                                filename,
                                job_id,
                            )

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

        except Exception as e:
            logger.error(f"Worker poll error: {str(e)}")

        await asyncio.sleep(5)
