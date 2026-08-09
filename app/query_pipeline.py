from llama_index.core import PromptTemplate, Settings, VectorStoreIndex
from llama_index.core.vector_stores import ExactMatchFilter, MetadataFilters

from app.embeddings import get_embed_model
from app.llm import get_llm
from app.vector_store import get_storage_context, get_vector_store

VALID_SOURCE_TYPES = ["lecture_slides", "reference_book", "past_paper"]

ROUTING_PROMPT_TMPL = """
You are an intelligent routing agent for an academic database.
Your job is to read the user's query and decide which data source is most appropriate to search.

Data Sources:
1. 'reference_book': Best for deep theory, formal definitions, and complex mathematical concepts.
2. 'lecture_slides': Best for high-level summaries, advantages/disadvantages, and general overviews.
3. 'past_paper': Best for exam patterns, frequently asked questions, and what to study for the test.

User Query: "{query}"

Output ONLY the exact string of the chosen source: lecture_slides, reference_book, or past_paper. Do not add any punctuation or extra words.
"""

QA_PROMPT_TMPL_STR = (
    "You are CourseLens, an expert academic advisor system.\n"
    "Below is context retrieved from the student's course materials:\n"
    "---------------------\n"
    "{context_str}\n"
    "---------------------\n"
    "Using ONLY the provided context, answer the following question.\n"
    "If the answer is not contained in the context, say 'I cannot find the answer in the provided materials.' Do not guess.\n"
    "IMPORTANT: You must cite your claims by referencing the source material at the end of your sentences (e.g., [Source: lecture_slides]).\n"
    "Question: {query_str}\n"
    "Advisor Answer: "
)


def get_routing_decision(query: str, llm) -> str:
    print("Analyzing query intent...")
    response = llm.complete(ROUTING_PROMPT_TMPL.format(query=query))
    decision = str(response).strip().lower()

    if decision not in VALID_SOURCE_TYPES:
        decision = "lecture_slides"

    return decision


def answer_query(query_text: str):
    print("Loading models...")
    Settings.embed_model = get_embed_model()
    Settings.llm = get_llm()

    vector_store = get_vector_store()
    storage_context = get_storage_context(vector_store)
    index = VectorStoreIndex.from_vector_store(vector_store, storage_context=storage_context)

    target_source = get_routing_decision(query_text, Settings.llm)
    print(f"Router decision: directing search to -> {target_source.upper()}")

    filters = MetadataFilters(filters=[ExactMatchFilter(key="source_type", value=target_source)])
    qa_prompt_tmpl = PromptTemplate(QA_PROMPT_TMPL_STR)

    query_engine = index.as_query_engine(
        similarity_top_k=3,
        filters=filters,
        text_qa_template=qa_prompt_tmpl,
    )

    print("Searching database...")
    response = query_engine.query(query_text)

    return target_source, response
