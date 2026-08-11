"""Shared FastAPI dependencies."""

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from api.db import get_db
from api.models import User
from api.schemas.auth import UserOut
from api.security import decode_access_token

_bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> UserOut:
    try:
        user_id = decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return UserOut(id=user.id, email=user.email, name=user.name)


def get_session_or_404(session_id: str, user: UserOut = Depends(get_current_user)) -> str:
    """TODO: look up session_id in the database, scoped to the current
    user, and 404 if it doesn't exist or isn't theirs. For now just echoes
    the id back so routers can depend on this and be wired correctly later
    -- the Session model doesn't exist yet (see api/models.py).
    """
    return session_id
