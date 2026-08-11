from datetime import datetime

from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: str
    file_name: str
    size_bytes: int
    source_type: str | None = None  # set once ingestion classifies it, per app/chunking.py
    uploaded_at: datetime


class UploadResponse(BaseModel):
    documents: list[DocumentOut]
    ingestion_status: str  # "ingesting" once BackgroundTasks picks it up


class IngestStatusOut(BaseModel):
    session_id: str
    status: str  # "empty" | "ingesting" | "ready" | "failed"
    documents_ingested: int
    error: str | None = None
