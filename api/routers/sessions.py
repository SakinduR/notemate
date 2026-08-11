import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session as DBSession

from api.db import get_db
from api.dependencies import get_current_user, get_session_or_404
from api.models import Session as SessionModel
from api.schemas.auth import UserOut
from api.schemas.sessions import DashboardOut, SessionCreateRequest, SessionOut, SessionUpdateRequest
from app.vector_store import delete_collection

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _to_session_out(session: SessionModel) -> SessionOut:
    return SessionOut(
        id=session.id,
        name=session.name,
        document_count=len(session.documents),
        created_at=session.created_at,
        ingestion_status=session.ingestion_status,
    )


@router.get("", response_model=DashboardOut)
def list_sessions(user: UserOut = Depends(get_current_user), db: DBSession = Depends(get_db)) -> DashboardOut:
    """The dashboard: every session (uploaded-doc workspace) this user owns."""
    sessions = (
        db.query(SessionModel)
        .filter(SessionModel.user_id == user.id)
        .order_by(SessionModel.created_at.desc())
        .all()
    )
    return DashboardOut(sessions=[_to_session_out(s) for s in sessions])


@router.post("", response_model=SessionOut)
def create_session(
    payload: SessionCreateRequest,
    user: UserOut = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> SessionOut:
    # The session's Chroma collection (session.chroma_collection_name) isn't
    # created here -- chromadb.get_or_create_collection (app/vector_store.py)
    # creates it lazily on first ingestion, so an unused session never leaves
    # an empty collection behind.
    session = SessionModel(user_id=user.id, name=payload.name)
    db.add(session)
    db.commit()
    db.refresh(session)
    return _to_session_out(session)


@router.get("/{session_id}", response_model=SessionOut)
def get_session(session: SessionModel = Depends(get_session_or_404)) -> SessionOut:
    return _to_session_out(session)


@router.patch("/{session_id}", response_model=SessionOut)
def update_session(
    payload: SessionUpdateRequest,
    session: SessionModel = Depends(get_session_or_404),
    db: DBSession = Depends(get_db),
) -> SessionOut:
    session.name = payload.name
    db.commit()
    db.refresh(session)
    return _to_session_out(session)


@router.delete("/{session_id}", status_code=204)
def delete_session(session: SessionModel = Depends(get_session_or_404), db: DBSession = Depends(get_db)) -> Response:
    # Best-effort cleanup of the Chroma collection and raw files -- neither
    # existing is fine (a session with nothing ever uploaded to it has
    # neither). The Document rows themselves cascade via the relationship's
    # cascade="all, delete-orphan" (see api/models.py), so no manual delete
    # is needed for those.
    delete_collection(session.chroma_collection_name)
    if Path(session.data_dir).exists():
        shutil.rmtree(session.data_dir)

    db.delete(session)
    db.commit()
    return Response(status_code=204)
