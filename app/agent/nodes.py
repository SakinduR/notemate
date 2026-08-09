"""Nodes for the corrective-RAG graph.

A LangGraph node is just a function: `(GraphState) -> dict`. It reads
whatever keys it needs from state and returns a dict of only the keys it
wants to update (see state.py's docstring for how those get merged back in).
Nodes don't call each other directly or know what comes next -- the edges
defined in graph.py decide execution order. That decoupling is what makes
the corrective loop (retry retrieval if grading says it's weak) possible:
the node itself doesn't need to know it might run twice.

retrieve_node below is fully implemented as a worked example. Everything
else is a stub: the docstring is the contract (what to read from state, what
to return), the body is yours.
"""

from llama_index.core import Settings, VectorStoreIndex

from app.agent.state import GraphState
from app.embeddings import get_embed_model
from app.vector_store import get_storage_context, get_vector_store

from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import PromptTemplate

# LlamaIndex's retriever needs Settings.embed_model to embed the query text
# -- it defaults to OpenAI and errors without an OPENAI_API_KEY otherwise.
# Set once at import time rather than inside retrieve_node, since
# HuggingFaceEmbedding(...) reloads model weights on every construction and
# a graph node can run many times in one process.
Settings.embed_model = get_embed_model()


def retrieve_node(state: GraphState) -> dict:
    """Fetch candidate chunks from Chroma for the current search query.

    Reuses the same LlamaIndex + Chroma wiring as the CLI query pipeline
    (app/vector_store.py) -- the retrieval mechanics don't change just
    because an agent is calling it instead of a script.
    """
    vector_store = get_vector_store()
    storage_context = get_storage_context(vector_store)
    index = VectorStoreIndex.from_vector_store(vector_store, storage_context=storage_context)

    retriever = index.as_retriever(similarity_top_k=6)
    retrieved_nodes = retriever.retrieve(state["query"])

    return {
        "retrieved_nodes": retrieved_nodes,
        "trace": [f"Retrieved {len(retrieved_nodes)} candidate chunks for query: {state['query']!r}"],
    }


def rewrite_query_node(state: GraphState) -> dict:
    """TODO: produce a search query for this pass.

    On the first pass this can just be state["original_query"] unchanged.
    On a retry (state["retry_count"] > 0, i.e. grading rejected too much of
    the last retrieval), use a small local model -- this is the "cheap
    Ollama step" from the plan -- to rewrite the query into something more
    likely to retrieve well (e.g. expand an acronym, drop conversational
    filler, make an implicit comparison explicit).

    Read:   state["original_query"], state["retry_count"]
    Return: {"query": <str>, "trace": [<short message describing the query used>]}
    """

    original_query = state.get("original_query", "")
    retry_count = state.get("retry_count", 0)

    trace = state.get("trace", [])

    if retry_count > 0:
        # Use a small local model to rewrite the query
        state["trace"].append(f"Retry {state['retry_count']}: rewriting query for better retrieval.")
        
        llm = ChatOllama(model="llama3", temperature=0)

        prompt = PromptTemplate.from_template(
            "You are an expert at optimizing search queries. "
            "Rewrite the following user question to be a highly effective keyword search query. "
            "Expand acronyms, drop conversational filler, and focus on key terms. "
            "Return ONLY the rewritten query as a single string. Do not include quotes or conversational text.\n\n"
            "Question: {question}")

        chain = prompt | llm
        rewritten_query = chain.invoke({"question": original_query}).content.strip()

        query = rewritten_query
        trace.append(f"Rewritten query: {query!r}")
    else:
        query = original_query
        trace.append(f"Using original query: {query!r}")

    return{
        "query": query,
        "trace": trace
    }


def rerank_node(state: GraphState) -> dict:
    """TODO: re-score state["retrieved_nodes"] against state["query"] with a
    local cross-encoder (e.g. bge-reranker-base) and sort by that score.

    This is the concrete "differentiate on retrieval quality" mechanism from
    the plan -- vector similarity alone is a coarse filter; a cross-encoder
    scores query+chunk pairs directly and is noticeably better at ranking.

    Read:   state["query"], state["retrieved_nodes"]
    Return: {"retrieved_nodes": <reranked list>, "trace": [...]}
    """
    raise NotImplementedError


def grade_documents_node(state: GraphState) -> dict:
    """TODO: for each chunk in state["retrieved_nodes"], ask a small local
    LLM (Ollama) a yes/no: "is this actually relevant to the question?" and
    keep only the ones graded relevant.

    This -- not the old hard category filter -- is what should decide what
    context the answer is allowed to use. It's also what route_after_grading
    (in graph.py) will inspect to decide whether to loop back to
    rewrite_query_node or move on.

    Read:   state["original_query"], state["retrieved_nodes"]
    Return: {"relevant_nodes": <filtered list>, "trace": [...]}
    """
    raise NotImplementedError


def generate_answer_node(state: GraphState) -> dict:
    """TODO: generate the final answer from state["relevant_nodes"], via
    Groq (primary) or Gemini (fallback) per the plan -- this is the one
    generation step worth spending a "real" model on.

    Always answer state["original_query"], not the possibly-rewritten
    state["query"]. Preserve per-chunk citation metadata (source file, page
    number) in the prompt/context so the answer can cite specifics, the way
    the old qa_prompt_tmpl in query_pipeline.py did.

    Read:   state["original_query"], state["relevant_nodes"]
    Return: {"answer": <str>, "trace": [...]}
    """
    raise NotImplementedError


def check_groundedness_node(state: GraphState) -> dict:
    """TODO: ask a small local LLM (Ollama) whether state["answer"] is
    actually supported by state["relevant_nodes"], to catch cases where
    generation drifted or hallucinated despite decent context.

    Read:   state["answer"], state["relevant_nodes"]
    Return: {"is_grounded": <bool>, "trace": [...]}
    """
    raise NotImplementedError
