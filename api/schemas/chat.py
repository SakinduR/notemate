from pydantic import BaseModel


class ChatRequest(BaseModel):
    query: str


class Citation(BaseModel):
    file_name: str
    page: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    trace: list[str]  # step-by-step agent trace, see app/agent/state.py
