from fastapi import APIRouter, Depends

from api.dependencies import get_session_or_404
from api.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/sessions", tags=["chat"])


@router.post("/{session_id}/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, session_id: str = Depends(get_session_or_404)) -> ChatResponse:
    """TODO: build the session's GraphState and invoke app.agent.graph against
    the session-scoped Chroma collection (see app/agent/graph.py::build_graph).

    This is a plain request/response for now; the plan calls for streaming
    the trace over SSE as the graph runs instead of returning it all at once
    -- swap this for a StreamingResponse once the graph side is stable and
    ready to wire in, rather than building both at once.
    """
    return ChatResponse(
        answer=f"(dummy answer for session {session_id!r}, query: {payload.query!r})",
        citations=[],
        trace=["This is a dummy response -- chat is not wired to the agent yet."],
    )
