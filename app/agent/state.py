"""Shared state schema for the corrective-RAG LangGraph pipeline.

In LangGraph, the graph's "state" is just a single dict-like object that gets
passed to every node. Each node is a plain function: it reads whatever keys
it needs out of state, does its work, and returns a dict of only the keys it
wants to change. LangGraph merges that returned dict back into the running
state before calling the next node -- a node never has to know or update the
full state, just its own slice of it.

`GraphState` is a TypedDict describing the shape of that state so nodes get
type-checking/autocomplete for `state["..."]`. Nothing here executes graph
logic; it's purely the contract every node in nodes.py reads from and writes
to. See the module docstring in nodes.py and graph.py for how it's used.
"""

import operator
from typing import Annotated, TypedDict

from llama_index.core.schema import NodeWithScore


class GraphState(TypedDict):
    # The user's question, exactly as asked. Never mutated by any node --
    # generate_answer_node should always answer *this*, even if the search
    # query itself got rewritten along the way.
    original_query: str

    # The query actually used for retrieval. Starts equal to original_query;
    # rewrite_query_node may replace it with a better search query on a
    # corrective retry.
    query: str

    # Raw candidate chunks pulled straight from Chroma.
    retrieved_nodes: list[NodeWithScore]

    # Chunks that survived reranking + relevance grading -- what
    # generate_answer_node is actually allowed to use as context.
    relevant_nodes: list[NodeWithScore]

    # The generated answer text.
    answer: str

    # Result of the groundedness check: is `answer` actually supported by
    # `relevant_nodes`, or did the model drift/hallucinate?
    is_grounded: bool

    # How many rewrite -> retrieve -> grade loops have run. Used to cap
    # retries (see the plan: max ~2) so a stubborn query can't loop forever.
    retry_count: int

    # How many times generate_answer_node has run. A separate counter from
    # retry_count: this caps the generate -> check_groundedness -> regenerate
    # loop (plan: "regenerate once, else return with a caveat"), which is a
    # different loop from the rewrite/retrieve correction loop above.
    generation_attempts: int

    # Annotated[..., operator.add] is a LangGraph "reducer": instead of each
    # node's return value overwriting state["trace"], LangGraph concatenates
    # (list + list) it onto the existing value. So every node can just
    # return {"trace": ["did the thing"]} and they all accumulate into one
    # ordered log -- this is what step 3's SSE endpoint will stream to the
    # frontend as the visible reasoning trace.
    trace: Annotated[list[str], operator.add]
