import asyncio
import logging
from services.clients import embedding_model, supabase, groq_client

logger = logging.getLogger("ai-service")


async def run_rag_pipeline(question: str) -> str:
    """
    Full RAG pipeline with parent-child retrieval:
    1. Embed the user question (offloaded to thread pool)
    2. Vector search on child chunks
    3. Retrieve parent content for full context (done by SQL function)
    4. Deduplicate by parent content prefix
    5. Build augmented prompt with source annotations
    6. Generate answer via Groq LLM
    """
    # Step 1: Embed the question (CPU-bound, run in thread pool)
    logger.info("Embedding the user question...")
    question_embedding = await asyncio.to_thread(
        embedding_model.encode, question
    )
    question_embedding = question_embedding.tolist()

    # Step 2: Vector search (I/O-bound, Supabase SDK is sync)
    logger.info("Searching vector database for context...")
    response = await asyncio.to_thread(
        lambda: supabase.rpc(
            "match_documents",
            {
                "query_embedding": question_embedding,
                "match_threshold": 0.2,
                "match_count": 5,
            },
        ).execute()
    )

    retrieved_docs = response.data

    # Step 3: Build context with dedup and source annotations
    context_text = ""
    seen_parent_prefixes: set[str] = set()

    if retrieved_docs:
        logger.info(f"Found {len(retrieved_docs)} relevant context pieces.")

        for doc in retrieved_docs:
            parent_content = doc["content"]
            child_content = doc.get("child_content", parent_content)
            source_file = doc.get("source_filename") or "unknown"
            section = doc.get("section_title") or ""
            page = doc.get("page_number")
            similarity = doc.get("similarity", 0)
            parent_id = doc.get("parent_id")

            # Deduplicate: same parent may be hit by multiple child chunks
            content_key = parent_content[:100]
            if content_key in seen_parent_prefixes:
                logger.debug(f"Skipping duplicate parent (sim={similarity:.3f})")
                continue
            seen_parent_prefixes.add(content_key)

            logger.debug(
                f"Hit: sim={similarity:.3f} | file={source_file} | "
                f"page={page} | parent_id={parent_id} | "
                f"child_preview={child_content[:60]!r}"
            )

            # Build source label for LLM citation
            source_label = source_file
            if section:
                source_label += f" - {section}"
            if page:
                source_label += f" - page {page}"

            context_text += f"[Source: {source_label}]\n{parent_content}\n\n"

    else:
        logger.info("No highly relevant context found in database.")
        context_text = "No specific internal company context found."

    system_prompt = f"""
    You are an elite enterprise AI assistant.

    INSTRUCTIONS:
    1. Answer the user's question strictly using the CONTEXT provided below.
    2. If the CONTEXT does not contain the answer, reply EXACTLY with: "I do not have enough internal information to answer this question." Do not guess or use outside knowledge.
    3. Format your response cleanly using markdown if necessary (bullet points, bold text).
    4. When citing information, reference the source label shown in brackets.

    --- Context ---
    {context_text}
    """

    # Step 4: Generate answer (I/O-bound, Groq client is async)
    logger.info("Sending augmented prompt to Groq LLM...")
    chat_completion = await groq_client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        model="llama-3.1-8b-instant",
        temperature=0.3,
        max_tokens=1024,
    )

    answer = chat_completion.choices[0].message.content
    logger.info("RAG pipeline completed successfully.")
    return answer
