import re
from collections import defaultdict

from llama_index.core.node_parser import SemanticSplitterNodeParser, SentenceSplitter
from llama_index.core.schema import BaseNode, Document, TextNode

EXCLUDED_EMBED_METADATA_KEYS = [
    "file_name", "file_path", "file_type", "file_size",
    "creation_date", "last_modified_date", "last_accessed_date",
]

SOURCE_TYPES = ["lecture_slides", "reference_book", "past_paper", "general_notes"]

# Exam-style structural cues (numbered questions, mark allocations, exam
# instructions). Calibrated against a real dataset: ~65-75% of individual
# past-paper pages match at least one pattern, vs a ~0.1% stray match rate on
# dense prose pages. A single stray page is expected by chance in a large
# enough document, so classification uses a fraction-of-pages threshold at
# the file level rather than a single-page trigger.
PAST_PAPER_PATTERNS = [
    re.compile(r"\bquestion\s+\d+\b", re.IGNORECASE),
    re.compile(r"\(\s*\d{1,3}\s*marks?\s*\)", re.IGNORECASE),
    re.compile(r"\banswer\s+(all|any)\b", re.IGNORECASE),
    re.compile(r"\btime\s*:\s*\d+\s*(hours?|hrs?)\b", re.IGNORECASE),
]
PAST_PAPER_PAGE_FRACTION_THRESHOLD = 0.3
SLIDE_MEDIAN_WORD_COUNT_THRESHOLD = 150
EMPTY_FILE_WORD_COUNT_THRESHOLD = 5


def _page_matches_past_paper_pattern(text: str) -> bool:
    return any(pattern.search(text) for pattern in PAST_PAPER_PATTERNS)


def detect_source_type(pages: list[Document]) -> str:
    """Classify a file's source type from its own content, not its file name."""
    word_counts = sorted(len(page.text.split()) for page in pages)
    median_word_count = word_counts[len(word_counts) // 2]

    if median_word_count < EMPTY_FILE_WORD_COUNT_THRESHOLD:
        return "general_notes"

    past_paper_page_fraction = sum(
        1 for page in pages if _page_matches_past_paper_pattern(page.text)
    ) / len(pages)
    if past_paper_page_fraction >= PAST_PAPER_PAGE_FRACTION_THRESHOLD:
        return "past_paper"

    if median_word_count < SLIDE_MEDIAN_WORD_COUNT_THRESHOLD:
        return "lecture_slides"

    return "reference_book"


def route_documents(
    documents: list[Document],
    type_overrides: dict[str, str] | None = None,
) -> dict[str, list[Document]]:
    """Group documents by source type for chunking-strategy selection.

    Type is auto-detected per file from page content (word density and
    exam-style patterns). `type_overrides` (file_name -> source_type) lets a
    caller pin a specific file's type instead, e.g. a user-selected hint from
    the upload UI.
    """
    type_overrides = type_overrides or {}
    routed: dict[str, list[Document]] = {source_type: [] for source_type in SOURCE_TYPES}

    pages_by_file: dict[str, list[Document]] = defaultdict(list)
    for doc in documents:
        doc.excluded_embed_metadata_keys = EXCLUDED_EMBED_METADATA_KEYS
        pages_by_file[doc.metadata.get("file_name", "")].append(doc)

    print("Detecting document types from content...")
    for file_name, pages in pages_by_file.items():
        override = type_overrides.get(file_name)
        source_type = override if override in SOURCE_TYPES else detect_source_type(pages)

        for page in pages:
            page.metadata["source_type"] = source_type
            routed[source_type].append(page)

    return routed


def _chunk_reference_books(docs: list[Document], embed_model) -> list[BaseNode]:
    if not docs:
        return []
    print(f"Applying Semantic Chunking to {len(docs)} reference book pages...")
    parser = SemanticSplitterNodeParser(
        buffer_size=1,
        breakpoint_percentile_threshold=95,
        embed_model=embed_model,
    )
    return parser.get_nodes_from_documents(docs)


def _chunk_lecture_slides(docs: list[Document]) -> list[BaseNode]:
    if not docs:
        return []
    print(f"Applying Structural Chunking to {len(docs)} slide pages...")
    parser = SentenceSplitter(chunk_size=256, chunk_overlap=20)
    return parser.get_nodes_from_documents(docs)


def _chunk_past_papers(docs: list[Document]) -> list[BaseNode]:
    if not docs:
        return []
    print(f"Applying Agentic Extraction to {len(docs)} past paper pages...")
    nodes = []
    for doc in docs:
        # TODO(step 2): replace with a real LLM extraction call via the LangGraph
        # ingestion pipeline. This still simulates the output to prove the
        # architecture without needing an extraction agent yet.
        simulated_llm_extracted_question = "Question 1: Explain the advantages of QPSK modulation."
        nodes.append(
            TextNode(
                text=simulated_llm_extracted_question,
                metadata={
                    **doc.metadata,
                    "extracted_by_agent": True,
                    "estimated_topic": "Modulation Techniques",
                },
            )
        )
    return nodes


def _chunk_general_notes(docs: list[Document]) -> list[BaseNode]:
    if not docs:
        return []
    parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)
    return parser.get_nodes_from_documents(docs)


def chunk_documents(routed: dict[str, list[Document]], embed_model) -> list[BaseNode]:
    nodes: list[BaseNode] = []
    nodes.extend(_chunk_reference_books(routed["reference_book"], embed_model))
    nodes.extend(_chunk_lecture_slides(routed["lecture_slides"]))
    nodes.extend(_chunk_past_papers(routed["past_paper"]))
    nodes.extend(_chunk_general_notes(routed["general_notes"]))
    return nodes
