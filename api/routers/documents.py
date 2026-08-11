import os
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session as DBSession

from api.db import SessionLocal, get_db
from api.dependencies import get_session_or_404
from api.models import Document as DocumentModel
from api.models import Session as SessionModel
from api.schemas.documents import DocumentOut, IngestStatusOut, UploadResponse
from app.ingest_pipeline import run_ingestion

router = APIRouter(prefix="/sessions", tags=["documents"])

# See README's "Unauthenticated public upload endpoint = abuse vector" risk --
# a strict size cap and type allowlist are the minimum guard for a public
# endpoint that writes to disk.
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {"application/pdf"}


def _to_document_out(document: DocumentModel) -> DocumentOut:
    return DocumentOut(
        id=document.id,
        file_name=document.file_name,
        size_bytes=document.size_bytes,
        source_type=document.source_type,
        uploaded_at=document.uploaded_at,
    )


def _run_ingestion_task(session_id: str) -> None:
    """Runs after the upload response has already been sent, so it can't
    reuse the request-scoped DB session from get_db (closed by then) --
    it opens its own.
    """
    db = SessionLocal()
    try:
        session = db.get(SessionModel, session_id)
        if session is None:
            return

        try:
            _, source_types = run_ingestion(
                data_dir=session.data_dir,
                collection_name=session.chroma_collection_name,
            )
            for document in session.documents:
                if document.file_name in source_types:
                    document.source_type = source_types[document.file_name]
            session.ingestion_status = "ready"
            session.ingestion_error = None
        except Exception as exc:  # noqa: BLE001 -- a bad file shouldn't crash the worker, just mark this session failed
            session.ingestion_status = "failed"
            session.ingestion_error = str(exc)

        db.commit()
    finally:
        db.close()


@router.post("/{session_id}/documents", response_model=UploadResponse)
def upload_documents(
    background_tasks: BackgroundTasks,
    files: list[UploadFile],
    session: SessionModel = Depends(get_session_or_404),
    db: DBSession = Depends(get_db),
) -> UploadResponse:
    # Validate everything before writing anything, so a rejected batch never
    # leaves partially-written files with no matching Document row.
    validated: list[tuple[UploadFile, bytes]] = []
    for file in files:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Every uploaded file needs a file name")
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(status_code=415, detail=f"Unsupported file type for {file.filename!r}: {file.content_type}")

        contents = file.file.read()
        if len(contents) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"{file.filename} exceeds the {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB size limit",
            )
        validated.append((file, contents))

    os.makedirs(session.data_dir, exist_ok=True)

    documents = []
    for file, contents in validated:
        (Path(session.data_dir) / file.filename).write_bytes(contents)
        document = DocumentModel(session_id=session.id, file_name=file.filename, size_bytes=len(contents))
        db.add(document)
        documents.append(document)

    session.ingestion_status = "ingesting"
    db.commit()
    for document in documents:
        db.refresh(document)

    background_tasks.add_task(_run_ingestion_task, session.id)

    return UploadResponse(
        documents=[_to_document_out(d) for d in documents],
        ingestion_status=session.ingestion_status,
    )


@router.get("/{session_id}/documents", response_model=list[DocumentOut])
def list_documents(session: SessionModel = Depends(get_session_or_404)) -> list[DocumentOut]:
    return [_to_document_out(d) for d in session.documents]


@router.get("/{session_id}/ingest/status", response_model=IngestStatusOut)
def get_ingest_status(session: SessionModel = Depends(get_session_or_404)) -> IngestStatusOut:
    documents_ingested = sum(1 for d in session.documents if d.source_type is not None)
    return IngestStatusOut(
        session_id=session.id,
        status=session.ingestion_status,
        documents_ingested=documents_ingested,
        error=session.ingestion_error,
    )
