"""Nodes for the corrective-RAG graph.

A LangGraph node is just a function: `(GraphState) -> dict`. It reads
whatever keys it needs from state and returns a dict of only the keys it
wants to update (see state.py's docstring for how those get merged back in).
Nodes don't call each other directly or know what comes next -- the edges
defined in graph.py decide execution order. That decoupling is what makes
the corrective loop (retry retrieval if grading says it's weak) possible:
the node itself doesn't need to know it might run twice.
"""

from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from llama_index.core import Settings, VectorStoreIndex
from llama_index.core.schema import NodeWithScore
from sentence_transformers import CrossEncoder

from app.agent.state import GraphState
from app.config import settings
from app.embeddings import get_embed_model
from app.llm import get_llm
from app.vector_store import get_storage_context, get_vector_store

# LlamaIndex's retriever needs Settings.embed_model to embed the query text
# -- it defaults to OpenAI and errors without an OPENAI_API_KEY otherwise.
# Set once at import time rather than inside retrieve_node, since
# HuggingFaceEmbedding(...) reloads model weights on every construction and
# a graph node can run many times in one process.
Settings.embed_model = get_embed_model()

# Shared clients/models, constructed once at import time rather than per
# node call:
#  - ChatOllama is a thin HTTP client (cheap to construct either way), but
#    sharing one instance across rewrite/grade/groundedness keeps things
#    consistent and avoids repeating the same construction three times.
#  - CrossEncoder actually loads model weights locally, same reason
#    Settings.embed_model is set once above -- reconstructing it per call
#    would reload the cross-encoder from disk on every rerank_node run.
#    (FlagEmbedding's FlagReranker was tried first since it's the model card's
#    suggested library, but its installed version calls a tokenizer method
#    that's been removed in the transformers version this project already
#    depends on for embeddings -- sentence-transformers' CrossEncoder runs
#    the same bge-reranker-base model without that conflict.)
_ollama_llm = ChatOllama(model=settings.ollama_model, base_url=settings.ollama_base_url, temperature=0)
_reranker = CrossEncoder(settings.reranker_model_name)

# Tuning constants for the two correction loops (see state.py's
# generation_attempts docstring for why there are two separate counters).
MAX_RETRIES = 2
MIN_RELEVANT_CHUNKS = 1
MAX_GENERATION_ATTEMPTS = 2

NO_ANSWER_MESSAGE = "I cannot find the answer in the provided materials."


def retrieve_node(state: GraphState) -> dict:
    """Fetch candidate chunks from Chroma for the current search query.

    Reuses the same LlamaIndex + Chroma wiring as the CLI query pipeline
    (app/vector_store.py) -- the retrieval mechanics don't change just
    because an agent is calling it instead of a script.
    """
    vector_store = get_vector_store(state["collection_name"])
    storage_context = get_storage_context(vector_store)
    index = VectorStoreIndex.from_vector_store(vector_store, storage_context=storage_context)

    retriever = index.as_retriever(similarity_top_k=6)
    retrieved_nodes = retriever.retrieve(state["query"])

    return {
        "retrieved_nodes": retrieved_nodes,
        "trace": [f"Retrieved {len(retrieved_nodes)} candidate chunks for query: {state['query']!r}"],
    }


_REWRITE_PROMPT = PromptTemplate.from_template(
    "You are an expert at optimizing search queries. "
    "Rewrite the following user question to be a highly effective keyword search query. "
    "Expand acronyms, drop conversational filler, and focus on key terms. "
    "Return ONLY the rewritten query as a single string. Do not include quotes or conversational text.\n\n"
    "Question: {question}"
)


def rewrite_query_node(state: GraphState) -> dict:
    """Produce a search query for this pass.

    On the first pass this is just the original query unchanged. On a retry
    (grading rejected too much of the last retrieval), ask the small local
    Ollama model to rewrite it into something more likely to retrieve well.
    """
    original_query = state.get("original_query", "")
    retry_count = state.get("retry_count", 0)

    new_trace = []

    if retry_count > 0:
        new_trace.append(f"Retry {retry_count}: rewriting query for better retrieval.")

        chain = _REWRITE_PROMPT | _ollama_llm
        query = chain.invoke({"question": original_query}).content.strip()

        new_trace.append(f"Rewritten query: {query!r}")
    else:
        query = original_query
        new_trace.append(f"Using original query: {query!r}")

    return {"query": query, "trace": new_trace}


def rerank_node(state: GraphState) -> dict:
    """Re-score state["retrieved_nodes"] against state["query"] with a local
    cross-encoder and sort by that score.

    This is the concrete "differentiate on retrieval quality" mechanism from
    the plan -- vector similarity alone is a coarse filter; a cross-encoder
    scores query+chunk pairs directly and is noticeably better at ranking.
    """
    query = state["query"]
    retrieved_nodes = state["retrieved_nodes"]

    pairs = [[query, node.text] for node in retrieved_nodes]
    scores = _reranker.predict(pairs)

    reranked_nodes = [node for _, node in sorted(zip(scores, retrieved_nodes), key=lambda pair: pair[0], reverse=True)]

    return {
        "retrieved_nodes": reranked_nodes,
        "trace": [f"Reranked {len(reranked_nodes)} nodes"],
    }


_GRADE_PROMPT = PromptTemplate.from_template(
    "You are grading whether a retrieved passage could help answer a user's question.\n"
    "The passage may use different wording than the question -- e.g. an acronym where the "
    "question spells the term out (COCOMO / Constructive Cost Model), or vice versa. Judge "
    "relevance by meaning, not literal word overlap.\n"
    "Question: {question}\n"
    "Passage:\n{passage}\n\n"
    "Would this passage help answer the question, even partially? Reply with exactly one word: yes or no."
)


def grade_documents_node(state: GraphState) -> dict:
    """Grade each retrieved chunk for relevance with the small Ollama model,
    keeping only the ones judged relevant.

    This -- not the old hard category filter -- decides what context
    generate_answer_node is allowed to use. If nothing survives, bump
    retry_count so route_after_grading (graph.py) knows to loop back to
    rewrite_query_node instead of generating off no evidence.
    """
    question = state["original_query"]
    chain = _GRADE_PROMPT | _ollama_llm

    relevant_nodes: list[NodeWithScore] = []
    for node in state["retrieved_nodes"]:
        verdict = chain.invoke({"question": question, "passage": node.text}).content.strip().lower()
        if verdict.startswith("yes"):
            relevant_nodes.append(node)

    updates = {
        "relevant_nodes": relevant_nodes,
        "trace": [f"Graded {len(state['retrieved_nodes'])} chunks: {len(relevant_nodes)} relevant"],
    }

    if len(relevant_nodes) < MIN_RELEVANT_CHUNKS:
        updates["retry_count"] = state.get("retry_count", 0) + 1

    return updates


def _format_context(nodes: list[NodeWithScore]) -> str:
    if not nodes:
        return "(no relevant context was retrieved)"

    sections = []
    for i, node in enumerate(nodes, start=1):
        source = node.metadata.get("file_name", "unknown source")
        page = node.metadata.get("source", "?")
        sections.append(f"[{i}] Source: {source}, page {page}\n{node.text}")

    return "\n\n".join(sections)


_GENERATE_PROMPT_TMPL = (
    "You are CourseLens, an expert academic advisor.\n"
    "Use ONLY the context below to answer the question. The context may use different wording "
    "than the question -- e.g. an acronym where the question spells the term out (COCOMO / "
    "Constructive Cost Model), or vice versa -- so match by meaning, not literal word overlap. "
    'If the answer truly isn\'t supported by the context, respond with exactly: "{no_answer}"\n'
    "Cite every claim with the bracketed source tag it came from, e.g. [1].\n\n"
    "Context:\n{context}\n\n"
    "Question: {question}\n"
    "Answer:"
)


def generate_answer_node(state: GraphState) -> dict:
    """Generate the final answer from state["relevant_nodes"], via Groq
    (primary) or Gemini (fallback) per the plan.

    Always answers state["original_query"], not the possibly-rewritten
    state["query"]. Per-chunk citation metadata (source file, page number)
    is preserved in the context so the answer can cite specifics.
    """
    generation_attempts = state.get("generation_attempts", 0) + 1

    if not state["relevant_nodes"]:
        return {
            "answer": NO_ANSWER_MESSAGE,
            "generation_attempts": generation_attempts,
            "trace": ["No relevant chunks survived grading; skipping generation."],
        }

    context = _format_context(state["relevant_nodes"])
    prompt = _GENERATE_PROMPT_TMPL.format(
        no_answer=NO_ANSWER_MESSAGE, context=context, question=state["original_query"]
    )

    answer = None
    trace = []

    if settings.groq_api_key:
        try:
            groq_llm = ChatGroq(model=settings.groq_model, api_key=settings.groq_api_key, temperature=0)
            answer = groq_llm.invoke(prompt).content.strip()
            trace.append("Generated answer with Groq.")
        except Exception as exc:  # noqa: BLE001 -- any Groq failure should fall back, not crash the graph
            trace.append(f"Groq generation failed ({exc}); falling back to Gemini.")

    if answer is None:
        gemini_llm = get_llm()
        answer = str(gemini_llm.complete(prompt)).strip()
        trace.append("Generated answer with Gemini.")

    return {"answer": answer, "generation_attempts": generation_attempts, "trace": trace}


_GROUNDEDNESS_PROMPT = PromptTemplate.from_template(
    "You are checking whether an answer is fully supported by the given context.\n"
    "Context:\n{context}\n\n"
    "Answer: {answer}\n\n"
    "Is every claim in the answer supported by the context? Reply with exactly one word: yes or no."
)

_UNVERIFIED_CAVEAT = (
    "\n\n(Note: this answer could not be fully verified against the retrieved sources -- "
    "treat it with extra caution.)"
)


def check_groundedness_node(state: GraphState) -> dict:
    """Ask the small Ollama model whether state["answer"] is actually
    supported by state["relevant_nodes"], to catch generation that drifted
    or hallucinated despite decent context.

    If ungrounded and out of regeneration attempts (see
    route_after_groundedness in graph.py), append a caveat to the answer
    rather than silently returning it as if it were verified.
    """
    answer = state["answer"]

    if answer.strip() == NO_ANSWER_MESSAGE:
        return {"is_grounded": True, "trace": ["Answer is the 'no answer' fallback; skipping groundedness check."]}

    context = _format_context(state["relevant_nodes"])
    chain = _GROUNDEDNESS_PROMPT | _ollama_llm
    verdict = chain.invoke({"context": context, "answer": answer}).content.strip().lower()
    is_grounded = verdict.startswith("yes")

    updates = {
        "is_grounded": is_grounded,
        "trace": [f"Groundedness check: {'grounded' if is_grounded else 'not grounded'}"],
    }

    if not is_grounded and state.get("generation_attempts", 0) >= MAX_GENERATION_ATTEMPTS:
        updates["answer"] = answer + _UNVERIFIED_CAVEAT

    return updates


def route_after_grading(state: GraphState) -> str:
    """Decide whether to generate now or loop back for another retrieval pass.

    Routing functions used with add_conditional_edges only return the name
    of the next step -- they can't update state themselves, which is why
    grade_documents_node (above) is the one that bumps retry_count.
    """
    if state["relevant_nodes"]:
        return "generate"
    if state["retry_count"] <= MAX_RETRIES:
        return "retry"
    return "generate"  # out of retries; generate_answer_node will produce the "no answer" fallback


def route_after_groundedness(state: GraphState) -> str:
    """Decide whether to regenerate once or finish, per the plan: "if not
    grounded: regenerate once, else return with a caveat" (the caveat itself
    is applied in check_groundedness_node, not here).
    """
    if state["is_grounded"]:
        return "end"
    if state["generation_attempts"] < MAX_GENERATION_ATTEMPTS:
        return "regenerate"
    return "end"
