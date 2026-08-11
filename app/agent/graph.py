"""Graph wiring for the corrective-RAG pipeline.

    query -> rewrite -> retrieve -> rerank -> grade
          -> (loop back to rewrite if grading found too little, capped retries)
          -> generate -> check_groundedness
          -> (regenerate once if not grounded, else return)

LangGraph pointers for this shape:
  - add_conditional_edges(source, routing_fn, {"path_a": "node_a", "path_b": "node_b"})
    is how you branch: routing_fn(state) returns one of the dict keys, and the
    dict maps that key to the actual node name to go to.
  - A conditional edge whose routing_fn sometimes returns the name of a node
    *earlier* in the graph is how you build the retry loop -- LangGraph
    graphs aren't strictly DAGs, cycles are allowed as long as something
    (here: retry_count / generation_attempts) eventually forces a path to END.
  - Docs: https://langchain-ai.github.io/langgraph/concepts/low_level/
"""

from langgraph.graph import END, START, StateGraph

from app.agent.nodes import (
    check_groundedness_node,
    generate_answer_node,
    grade_documents_node,
    rerank_node,
    retrieve_node,
    rewrite_query_node,
    route_after_grading,
    route_after_groundedness,
)
from app.agent.state import GraphState


def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("rewrite_query", rewrite_query_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("rerank", rerank_node)
    graph.add_node("grade_documents", grade_documents_node)
    graph.add_node("generate_answer", generate_answer_node)
    graph.add_node("check_groundedness", check_groundedness_node)

    graph.add_edge(START, "rewrite_query")
    graph.add_edge("rewrite_query", "retrieve")
    graph.add_edge("retrieve", "rerank")
    graph.add_edge("rerank", "grade_documents")

    # route_after_grading reads state (already updated by grade_documents_node)
    # and returns "retry" or "generate" -- the dict below maps those strings
    # to the actual next node. "retry" points back to "rewrite_query", which
    # is the cycle that makes this a corrective loop instead of a straight line.
    graph.add_conditional_edges(
        "grade_documents",
        route_after_grading,
        {"retry": "rewrite_query", "generate": "generate_answer"},
    )

    graph.add_edge("generate_answer", "check_groundedness")
    graph.add_conditional_edges(
        "check_groundedness",
        route_after_groundedness,
        {"regenerate": "generate_answer", "end": END},
    )

    return graph.compile()


if __name__ == "__main__":
    # Quick manual smoke test: `python -m app.agent.graph` from the repo root.
    app = build_graph()
    result = app.invoke(
        {
            "collection_name": "course_materials",
            "original_query": "What is Constructive Cost Model?",
            "query": "What is Constructive Cost Model?",
            "retry_count": 0,
            "generation_attempts": 0,
            "trace": [],
        }
    )
    print("\n".join(result["trace"]))
    print(f"\nAnswer:\n{result['answer']}")
