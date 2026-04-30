import os
import time
import logging
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

# --- Integrations ---
from groq import AsyncGroq
from supabase import create_client, Client
from sentence_transformers import SentenceTransformer

# 1. Setup Logging and Environment
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ai-service")

# Load environment variables from .env file
load_dotenv()

# 2. Initialize Clients (Groq, Supabase, SentenceTransformers)
groq_api_key = os.getenv("GROQ_API_KEY")
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not all([groq_api_key, supabase_url, supabase_key]):
    logger.error("Missing critical environment variables. Check your .env file.")

# Initialize Groq async client
groq_client = AsyncGroq(api_key=groq_api_key)

# Initialize Supabase client
supabase: Client = create_client(supabase_url, supabase_key)

# Initialize the embedding model (Downloads automatically on first run, ~80MB)
# Produces 384-dimensional vectors.
logger.info("Loading embedding model...")
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
logger.info("Embedding model loaded successfully.")

# 3. FastAPI App Initialization
app = FastAPI(title="Enterprise RAG AI Service")

# --- Middleware ---
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"Path: {request.url.path} | Method: {request.method} | Status: {response.status_code} | Time: {process_time:.4f}s")
    return response

# --- Data Models ---
class AskRequest(BaseModel):
    question: str

class AskResponse(BaseModel):
    answer: str

class IngestRequest(BaseModel):
    text: str

class IngestResponse(BaseModel):
    message: str
    document_id: int

# --- Endpoints ---

# [DAY 8]: Ask LLM (Groq Integration)
@app.post("/ask", response_model=AskResponse)
async def ask_ai(request: AskRequest):
    """
    Takes a user question, sends it to Groq LLM (e.g., Llama 3), and returns the generated answer.
    """
    logger.info(f"Received question for LLM: '{request.question}'")
    
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        # Call Groq API using Llama-3 8B model
        chat_completion = await groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful, professional enterprise assistant. Answer concisely."
                },
                {
                    "role": "user",
                    "content": request.question
                }
            ],
            model="llama-3.1-8b-instant", 
            temperature=0.5,
            max_tokens=1024,
        )
        
        # Extract the real answer from Groq
        real_answer = chat_completion.choices[0].message.content
        
        return AskResponse(answer=real_answer)

    except Exception as e:
        logger.error(f"Error communicating with Groq API: {str(e)}")
        raise HTTPException(status_code=500, detail="AI generation failed.")


# [DAY 9]: Embed & Store (Vector Database Integration)
@app.post("/ingest", response_model=IngestResponse)
def ingest_knowledge(request: IngestRequest):
    """
    Takes plain text, converts it into a vector embedding, and stores it in Supabase (pgvector).
    Note: We use synchronous def here because SentenceTransformer is CPU-bound and Supabase client is sync.
    """
    logger.info("Received text for ingestion.")
    
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    try:
        # 1. Convert text to vector embedding
        # encode() returns a numpy array, we convert it to a standard Python list for JSON serialization
        vector_embedding = embedding_model.encode(request.text).tolist()

        # 2. Insert into Supabase 'documents' table
        data, count = supabase.table("documents").insert({
            "content": request.text,
            "embedding": vector_embedding
        }).execute()
        
        # Get the ID of the newly inserted row
        inserted_id = data[1][0]['id']
        logger.info(f"Successfully stored document with ID: {inserted_id}")

        return IngestResponse(
            message="Successfully embedded and stored in vector database.",
            document_id=inserted_id
        )

    except Exception as e:
        logger.error(f"Error during ingestion process: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to embed and store data.")


@app.get("/health")
async def health_check():
    return {"status": "Healthy", "service": "ai-service-with-groq-supabase"}