import os
import uuid
import logging
from fastapi import APIRouter, HTTPException, UploadFile, File
from models.schemas import UploadResponse, JobStatusResponse
from services.clients import supabase
from config import UPLOAD_DIR

logger = logging.getLogger("ai-service")
router = APIRouter()


@router.post("/upload", response_model=UploadResponse, status_code=202)
async def upload_document(file: UploadFile = File(...)):
    """Save uploaded PDF and create an async processing job."""
    logger.info(f"Received file: {file.filename}")
    if not file.filename or not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    try:
        file_id = str(uuid.uuid4())
        file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
        logger.info(f"File saved to {file_path}")

        job_id = str(uuid.uuid4())
        supabase.table("document_jobs").insert(
            {"id": job_id, "filename": file.filename, "status": "pending", "file_path": file_path}
        ).execute()

        logger.info(f"Job {job_id} created for file {file.filename}")
        return UploadResponse(job_id=job_id, message="File uploaded. Processing in background.")
    except Exception as e:
        logger.error(f"Error creating upload job: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create upload job.")


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Return current status of a document processing job."""
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
