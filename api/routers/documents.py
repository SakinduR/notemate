from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile

from api.dependencies import get_session_or_404
from api.schemas.documents import DocumentOut, IngestStatusOut, UploadResponse

router = APIRouter(prefix="/sessions", tags=["documents"])


@router.post("/{session_id}/documents", response_model=UploadResponse)
def upload_documents(
    background_tasks: BackgroundTasks,
    files: list[UploadFile],
    session_id: str = Depends(get_session_or_404),
) -> UploadResponse:
    """TODO:
    - validate file size/type (see README's "Unauthenticated public upload
      endpoint = abuse vector" risk -- size cap + type allowlist belong here)
    - save the raw files (Docker volume for now, OCI Object Storage later)
      to a session-scoped directory, not the shared app/config.py data_dir
    - background_tasks.add_task(...) to call app.ingest_pipeline.run_ingestion
      against a session-scoped Chroma collection, so upload doesn't block on
      parsing/embedding
    """
    return UploadResponse(
        documents=[
            DocumentOut(
                id="dummy-document-id",
                file_name=file.filename or "unknown",
                size_bytes=0,
                uploaded_at=datetime.now(timezone.utc),
            )
            for file in files
        ],
        ingestion_status="ingesting",
    )


@router.get("/{session_id}/ingest/status", response_model=IngestStatusOut)
def get_ingest_status(session_id: str = Depends(get_session_or_404)) -> IngestStatusOut:
    """TODO: track real ingestion progress/failures (e.g. a row updated by
    the background task) so the frontend can poll this instead of guessing
    when it's safe to enable the chat.
    """
    return IngestStatusOut(session_id=session_id, status="empty", documents_ingested=0)
