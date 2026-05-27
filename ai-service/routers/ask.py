import logging
from fastapi import APIRouter, HTTPException
from models.schemas import AskRequest, AskResponse
from services.rag import run_rag_pipeline

logger = logging.getLogger("ai-service")
router = APIRouter()


@router.post("/ask", response_model=AskResponse)
async def ask_ai(request: AskRequest):
    """RAG pipeline: embed question -> vector search -> generate answer."""
    logger.info(f"Processing RAG request for: '{request.question}'")
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    try:
        answer = await run_rag_pipeline(request.question)
        return AskResponse(answer=answer)
    except Exception as e:
        logger.error(f"Error in RAG pipeline: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate AI response.")
