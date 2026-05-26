import os
import sys
import time
import uuid
import asyncio
import logging
from datetime import datetime, timezone
from fastapi import FastAPI, Request, HTTPException, UploadFile, File
import io
from pypdf import PdfReader
from pydantic import BaseModel
from dotenv import load_dotenv


# --- Integrations ---
from groq import AsyncGroq
from supabase import create_client, Client
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 1. Setup Logging and Environment
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    handlers=[logging.StreamHandler(sys.stdout)])
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

class UploadResponse(BaseModel):
    job_id: str
    message: str

class JobStatusResponse(BaseModel):
    id: str
    filename: str
    status: str
    chunks_count: int | None = None
    error_message: str | None = None
    created_at: str
    completed_at: str | None = None

# --- Upload Directory ---
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "Uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- Endpoints ---

# [DAY 11]: The RAG Pipeline (Retrieve -> Augment -> Generate)
@app.post("/ask", response_model=AskResponse)
async def ask_ai(request: AskRequest):
    """
    The core RAG endpoint.
    1. Embed the user question.
    2. Vector search in Supabase.
    3. Inject context into LLM prompt.
    4. Generate and return answer.
    """
    logger.info(f"Processing RAG request for: '{request.question}'")
    
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        # STEP 1: Embed the user's question
        logger.info("Embedding the user question...")
        question_embedding = embedding_model.encode(request.question).tolist()

        # STEP 2: Retrieve relevant documents from Supabase using RPC (Remote Procedure Call)
        logger.info("Searching vector database for context...")
        response = supabase.rpc(
            "match_documents",
            {
                "query_embedding": question_embedding,
                "match_threshold": 0.2, # Lower threshold slightly for better recall
                "match_count": 5        # [DAY 12]: Increase Top-K to 5 chunks
            }
        ).execute()

        retrieved_docs = response.data
        
        # STEP 3: Augment the Prompt (Combine context and question)
        context_text = ""
        if retrieved_docs:
            logger.info(f"Found {len(retrieved_docs)} relevant context pieces.")
            for doc in retrieved_docs:
                context_text += f"- {doc['content']}\n"
        else:
            logger.info("No highly relevant context found in database.")
            context_text = "No specific internal company context found."

        # Build the dynamic System Prompt
        system_prompt = f"""
        You are an elite enterprise AI assistant.
        
        INSTRUCTIONS:
        1. Answer the user's question strictly using the CONTEXT provided below.
        2. If the CONTEXT does not contain the answer, reply EXACTLY with: "I do not have enough internal information to answer this question." Do not guess or use outside knowledge.
        3. Format your response cleanly using markdown if necessary (bullet points, bold text).
        
        --- Context ---
        {context_text}
        """

        # STEP 4: Generate (Call the Groq LLM)
        logger.info("Sending augmented prompt to Groq LLM...")
        chat_completion = await groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.question}
            ],
            model="llama-3.1-8b-instant", 
            temperature=0.3, # Lower temperature for more factual responses
            max_tokens=1024,
        )
        
        real_answer = chat_completion.choices[0].message.content
        logger.info("RAG pipeline completed successfully.")
        
        return AskResponse(answer=real_answer)

    except Exception as e:
        logger.error(f"Error in RAG pipeline: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate AI response.")


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

# Async Upload — creates a job and returns immediately
@app.post("/upload", response_model=UploadResponse, status_code=202)
async def upload_document(file: UploadFile = File(...)):
    """
    Saves the uploaded PDF and creates a processing job.
    Returns 202 Accepted with a job_id for status polling.
    """
    logger.info(f"Received file: {file.filename}")
    if not file.filename or not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    try:
        # Save file to disk
        file_id = str(uuid.uuid4())
        file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
        logger.info(f"File saved to {file_path}")

        # Create job record in database
        job_id = str(uuid.uuid4())
        supabase.table("document_jobs").insert({
            "id": job_id,
            "filename": file.filename,
            "status": "pending",
            "file_path": file_path,
        }).execute()

        logger.info(f"Job {job_id} created for file {file.filename}")
        return UploadResponse(job_id=job_id, message="File uploaded. Processing in background.")

    except Exception as e:
        logger.error(f"Error creating upload job: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create upload job.")


# Job status endpoint for frontend polling
@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Returns the current status of a document processing job."""
    try:
        response = supabase.table("document_jobs").select("*").eq("id", job_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Job not found.")

        job = response.data[0]
        return JobStatusResponse(
            id=job["id"],
            filename=job["filename"],
            status=job["status"],
            chunks_count=job.get("chunks_count"),
            error_message=job.get("error_message"),
            created_at=job["created_at"],
            completed_at=job.get("completed_at"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching job status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch job status.")


# --- Background Worker ---
async def process_document_jobs():
    """Background task that polls for pending jobs and processes them."""
    while True:
        try:
            # Fetch pending jobs
            response = supabase.table("document_jobs") \
                .select("*") \
                .eq("status", "pending") \
                .order("created_at") \
                .limit(5) \
                .execute()

            for job in response.data:
                job_id = job["id"]
                file_path = job["file_path"]
                logger.info(f"Processing job {job_id}: {job['filename']}")

                # Mark as processing
                supabase.table("document_jobs") \
                    .update({"status": "processing"}) \
                    .eq("id", job_id) \
                    .execute()

                try:
                    # Read and parse PDF
                    with open(file_path, "rb") as f:
                        pdf_bytes = f.read()
                    pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
                    extracted_text = "".join([page.extract_text() or "" for page in pdf_reader.pages])

                    if not extracted_text.strip():
                        raise ValueError("No readable text found in PDF.")

                    # Chunk the text
                    text_splitter = RecursiveCharacterTextSplitter(
                        chunk_size=500,
                        chunk_overlap=50,
                        separators=["\n\n", "\n", ".", " ", ""]
                    )
                    chunks = text_splitter.split_text(extracted_text)
                    logger.info(f"Job {job_id}: {len(chunks)} chunks to embed.")

                    # Embed and store each chunk
                    for chunk in chunks:
                        vector_embedding = embedding_model.encode(chunk).tolist()
                        supabase.table("documents").insert({
                            "content": chunk,
                            "embedding": vector_embedding
                        }).execute()

                    # Mark as completed
                    supabase.table("document_jobs").update({
                        "status": "completed",
                        "chunks_count": len(chunks),
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                    }).eq("id", job_id).execute()
                    logger.info(f"Job {job_id} completed: {len(chunks)} chunks stored.")

                except Exception as e:
                    logger.error(f"Job {job_id} failed: {str(e)}")
                    supabase.table("document_jobs").update({
                        "status": "failed",
                        "error_message": str(e),
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                    }).eq("id", job_id).execute()

        except Exception as e:
            logger.error(f"Worker poll error: {str(e)}")

        await asyncio.sleep(5)

@app.get("/health")
async def health_check():
    return {"status": "Healthy", "service": "ai-service-with-groq-supabase"}

@app.on_event("startup")
async def start_background_worker():
    asyncio.create_task(process_document_jobs())
    logger.info("Background document processing worker started.")