"""API-specific settings (DB, auth) -- kept separate from app/config.py since
the CLI scripts and the LangGraph agent don't need a database or JWT secret,
only the HTTP layer does.
"""

import os

from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class ApiSettings:
    database_url: str = os.getenv("DATABASE_URL", "")
    jwt_secret: str = os.getenv("JWT_SECRET", "")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))


settings = ApiSettings()
