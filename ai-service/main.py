from fastapi import FastAPI
from pydantic import BaseModel

# 1. Initialize the FastAPI application
app = FastAPI(
    title="Enterprise RAG AI Service",
    description="Microservice for handling LLM and RAG logic",
    version="1.0.0"
)

# 2. Define data models (Similar to C# Models/DTOs)
# Represents the incoming request payload
class AskRequest(BaseModel):
    question: str

# Represents the outgoing response payload
class AskResponse(BaseModel):
    answer: str

# 3. Define the API endpoint
@app.post("/ask", response_model=AskResponse)
async def ask_ai(request: AskRequest):
    """
    Endpoint to process user questions.
    Currently returns a mock response. Will integrate Azure OpenAI later.
    """
    
    # Check if the question is empty
    if not request.question.strip():
        return AskResponse(answer="Error: Question cannot be empty.")

    # Generate a fake response for Day 4
    mock_answer = f"[Mocked Python AI] I received your question: '{request.question}'. The real RAG pipeline will be ready in Week 2."
    
    return AskResponse(answer=mock_answer)

# 4. Health check endpoint for the Python service
@app.get("/health")
async def health_check():
    """
    Simple health check to ensure the Python service is running.
    """
    return {"status": "Healthy", "service": "ai-service"}