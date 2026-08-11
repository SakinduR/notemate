from datetime import datetime

from pydantic import BaseModel


class SessionCreateRequest(BaseModel):
    name: str


class SessionUpdateRequest(BaseModel):
    name: str


class SessionOut(BaseModel):
    id: str
    name: str
    document_count: int
    created_at: datetime
    ingestion_status: str  # "empty" | "ingesting" | "ready" | "failed"


class DashboardOut(BaseModel):
    sessions: list[SessionOut]
