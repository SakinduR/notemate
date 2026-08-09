"""Graph wiring for the corrective-RAG pipeline.

Only `retrieve_node` is wired in below, as a minimal working example: it
proves the state schema and one real node work end-to-end through
LangGraph, START -> retrieve -> END. Everything from here is yours to build
-- add_node for each stub in nodes.py, then add_edge/add_conditional_edges
to reproduce the graph shape from the plan:

    query -> rewrite? -> retrieve -> rerank -> grade
          -> (loop back to rewrite if grading found too little, capped retries)
          -> generate -> check_groundedness
          -> (regenerate once if not grounded, else return)

Some LangGraph pointers for wiring that shape:
  - add_conditional_edges(source, routing_fn, {"path_a": "node_a", "path_b": "node_b"})
    is how you branch: routing_fn(state) returns one of the dict keys.
  - A conditional edge whose routing_fn sometimes returns the name of a node
    *earlier* in the graph is how you build the retry loop -- LangGraph
    graphs aren't strictly DAGs, cycles are allowed as long as something
    (here: retry_count) eventually forces a path to END.
  - Docs: https://langchain-ai.github.io/langgraph/concepts/low_level/
"""

from langgraph.graph import END, START, StateGraph

from app.agent.nodes import retrieve_node
from app.agent.state import GraphState


def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("retrieve", retrieve_node)

    graph.add_edge(START, "retrieve")
    
    graph.add_edge("retrieve", END)  # TODO: replace once rerank/grade/etc. exist

    return graph.compile()


if __name__ == "__main__":
    # Quick manual smoke test: `python -m app.agent.graph` from the repo root.
    app = build_graph()
    result = app.invoke(
        {
            "original_query": "What is Constructive Cost Model?",
            "query": "What is Constructive Cost Model?",
            "retry_count": 0,
            "trace": [],
        }
    )
    print("\n".join(result["trace"]))
    print(f"\nRetrieved {len(result['retrieved_nodes'])} nodes.")
