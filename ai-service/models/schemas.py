from pydantic import BaseModel


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
