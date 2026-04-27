import time
import logging
from fastapi import FastAPI, Request
from pydantic import BaseModel

# 1. Configure Python's built-in logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("ai-service")

app = FastAPI(
    title="Enterprise RAG AI Service",
    description="Microservice for handling LLM and RAG logic",
    version="1.0.0"
)

# 2. Add a Middleware for global request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware to log every incoming HTTP request and its processing time.
    """
    start_time = time.time()
    
    # Process the request
    response = await call_next(request)
    
    # Calculate processing time
    process_time = time.time() - start_time
    
    # Log the details: Method, Path, Status Code, and Time
    logger.info(
        f"Path: {request.url.path} | Method: {request.method} | "
        f"Status: {response.status_code} | Time: {process_time:.4f}s"
    )
    
    return response

# 3. Data models
class AskRequest(BaseModel):
    question: str

class AskResponse(BaseModel):
    answer: str

# 4. API Endpoints
@app.post("/ask", response_model=AskResponse)
async def ask_ai(request: AskRequest):
    # Log the incoming question payload
    logger.info(f"Received question: '{request.question}'")
    
    if not request.question.strip():
        logger.warning("Empty question received.")
        return AskResponse(answer="Error: Question cannot be empty.")

    mock_answer = f"[Mocked Python AI] I received your question: '{request.question}'. The real RAG pipeline will be ready in Week 2."
    
    return AskResponse(answer=mock_answer)

@app.get("/health")
async def health_check():
    return {"status": "Healthy", "service": "ai-service"}