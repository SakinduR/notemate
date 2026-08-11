from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import models  # noqa: F401 -- registers model classes on Base.metadata before create_all
from api.db import Base, engine
from api.routers import auth, chat, documents, sessions

# TODO: swap for Alembic migrations once the schema needs to evolve without
# just adding tables (renames, column changes). create_all is idempotent and
# fine for this early stage -- it only creates tables that don't exist yet.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="NoteMate API")

# TODO: restrict to the actual frontend origin once it exists/is deployed;
# wide open is fine for local dev against the dummy handlers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(documents.router)
app.include_router(chat.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
