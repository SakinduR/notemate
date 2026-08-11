from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from api.dependencies import get_current_user, get_session_or_404
from api.schemas.auth import UserOut
from api.schemas.sessions import DashboardOut, SessionCreateRequest, SessionOut

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=DashboardOut)
def list_sessions(user: UserOut = Depends(get_current_user)) -> DashboardOut:
    """The dashboard: every session (uploaded-doc workspace) this user owns.

    TODO: query the database for sessions belonging to user.id.
    """
    return DashboardOut(
        sessions=[
            SessionOut(
                id="dummy-session-id",
                name="Example session",
                document_count=0,
                created_at=datetime.now(timezone.utc),
                ingestion_status="empty",
            )
        ]
    )


@router.post("", response_model=SessionOut)
def create_session(payload: SessionCreateRequest, user: UserOut = Depends(get_current_user)) -> SessionOut:
    """TODO: insert a new session row owned by user.id, and provision its
    Chroma collection (see app/vector_store.py -- one collection per session,
    not the single shared "course_materials" collection the CLI pipeline uses).
    """
    return SessionOut(
        id="dummy-session-id",
        name=payload.name,
        document_count=0,
        created_at=datetime.now(timezone.utc),
        ingestion_status="empty",
    )


@router.get("/{session_id}", response_model=SessionOut)
def get_session(session_id: str = Depends(get_session_or_404)) -> SessionOut:
    """TODO: fetch the real session row."""
    return SessionOut(
        id=session_id,
        name="Example session",
        document_count=0,
        created_at=datetime.now(timezone.utc),
        ingestion_status="empty",
    )
