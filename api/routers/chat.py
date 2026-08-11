import json
from collections.abc import Generator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from llama_index.core.schema import NodeWithScore

from api.dependencies import get_session_or_404
from api.models import Session as SessionModel
from api.schemas.chat import ChatRequest, ChatResponse, Citation
from app.agent.graph import build_graph

router = APIRouter(prefix="/sessions", tags=["chat"])

# Built once at import time -- compiling the graph is cheap (it's just
# wiring node functions together), but doing it per-request would be
# pointless work on every single chat call.
_agent = build_graph()


def _build_initial_state(session: SessionModel, query: str) -> dict:
    return {
        "collection_name": session.chroma_collection_name,
        "original_query": query,
        "query": query,
        "retry_count": 0,
        "generation_attempts": 0,
        "trace": [],
    }


def _extract_citations(relevant_nodes: list[NodeWithScore]) -> list[Citation]:
    seen = set()
    citations = []
    for node in relevant_nodes:
        file_name = node.metadata.get("file_name", "unknown source")
        page = str(node.metadata.get("source", "?"))
        if (file_name, page) not in seen:
            seen.add((file_name, page))
            citations.append(Citation(file_name=file_name, page=page))
    return citations


@router.post("/{session_id}/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, session: SessionModel = Depends(get_session_or_404)) -> ChatResponse:
    if session.ingestion_status != "ready":
        raise HTTPException(
            status_code=400,
            detail=f"Session isn't ready for chat yet (ingestion_status={session.ingestion_status!r})",
        )

    result = _agent.invoke(_build_initial_state(session, payload.query))

    return ChatResponse(
        answer=result["answer"],
        citations=_extract_citations(result["relevant_nodes"]),
        trace=result["trace"],
    )


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _stream_chat(initial_state: dict) -> Generator[str, None, None]:
    # LangGraph's .stream(stream_mode="updates") yields {node_name: update}
    # after each node runs -- update is the same partial dict a node returns
    # from .invoke(), so we accumulate it into `state` ourselves here rather
    # than calling .invoke() a second time (which would re-run every LLM
    # call). "trace" is the only Annotated/reducer field in GraphState
    # (concatenates -- see app/agent/state.py); every other key overwrites.
    state = dict(initial_state)
    try:
        for step in _agent.stream(initial_state, stream_mode="updates"):
            for node_name, update in step.items():
                for key, value in update.items():
                    if key == "trace":
                        state["trace"] = state.get("trace", []) + value
                        for message in value:
                            yield _sse("trace", {"node": node_name, "message": message})
                    else:
                        state[key] = value
    except Exception as exc:  # noqa: BLE001 -- surface any failure to the client instead of dropping the connection
        yield _sse("error", {"message": str(exc)})
        return

    citations = [c.model_dump() for c in _extract_citations(state.get("relevant_nodes", []))]
    yield _sse("final", {"answer": state.get("answer", ""), "citations": citations})


@router.post("/{session_id}/chat/stream")
def chat_stream(payload: ChatRequest, session: SessionModel = Depends(get_session_or_404)) -> StreamingResponse:
    if session.ingestion_status != "ready":
        raise HTTPException(
            status_code=400,
            detail=f"Session isn't ready for chat yet (ingestion_status={session.ingestion_status!r})",
        )

    initial_state = _build_initial_state(session, payload.query)
    return StreamingResponse(_stream_chat(initial_state), media_type="text/event-stream")
