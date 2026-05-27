import logging
from services.clients import embedding_model, supabase, groq_client

logger = logging.getLogger("ai-service")


async def run_rag_pipeline(question: str) -> str:
    """
    Full RAG pipeline:
    1. Embed the user question
    2. Vector search in Supabase
    3. Build augmented prompt with retrieved context
    4. Generate answer via Groq LLM
    """
    # Step 1: Embed the question
    logger.info("Embedding the user question...")
    question_embedding = embedding_model.encode(question).tolist()

    # Step 2: Vector search
    logger.info("Searching vector database for context...")
    response = supabase.rpc(
        "match_documents",
        {
            "query_embedding": question_embedding,
            "match_threshold": 0.2,
            "match_count": 5,
        },
    ).execute()

    retrieved_docs = response.data

    # Step 3: Build context
    context_text = ""
    if retrieved_docs:
        logger.info(f"Found {len(retrieved_docs)} relevant context pieces.")
        for doc in retrieved_docs:
            context_text += f"- {doc['content']}\n"
    else:
        logger.info("No highly relevant context found in database.")
        context_text = "No specific internal company context found."

    system_prompt = f"""
    You are an elite enterprise AI assistant.

    INSTRUCTIONS:
    1. Answer the user's question strictly using the CONTEXT provided below.
    2. If the CONTEXT does not contain the answer, reply EXACTLY with: "I do not have enough internal information to answer this question." Do not guess or use outside knowledge.
    3. Format your response cleanly using markdown if necessary (bullet points, bold text).

    --- Context ---
    {context_text}
    """

    # Step 4: Generate answer
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
