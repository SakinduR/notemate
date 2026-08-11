"""Shared FastAPI dependencies."""

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session as DBSession

from api.db import get_db
from api.models import Session as SessionModel
from api.models import User
from api.schemas.auth import UserOut
from api.security import decode_access_token

_bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: DBSession = Depends(get_db),
) -> UserOut:
    try:
        user_id = decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return UserOut(id=user.id, email=user.email, name=user.name)


def get_session_or_404(
    session_id: str,
    user: UserOut = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> SessionModel:
    """Looks up session_id, scoped to the current user. 404s for both "does
    not exist" and "exists but isn't yours" -- deliberately not a 403, so a
    caller can't distinguish the two and enumerate other users' session ids.
    """
    session = db.get(SessionModel, session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
