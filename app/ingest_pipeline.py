from llama_index.core import Settings, VectorStoreIndex

from app.chunking import chunk_documents, route_documents
from app.embeddings import get_embed_model
from app.loaders import load_documents
from app.vector_store import get_storage_context, get_vector_store


def run_ingestion(
    data_dir: str | None = None,
    type_overrides: dict[str, str] | None = None,
    collection_name: str | None = None,
) -> tuple[int, dict[str, str]]:
    """Returns (node_count, source_types) where source_types maps each
    file_name to the source_type app/chunking.py classified it as -- callers
    that track per-document metadata (e.g. api/routers/documents.py) use
    this instead of re-deriving it themselves.
    """
    print("Loading embedding model...")
    Settings.embed_model = get_embed_model()
    Settings.llm = None

    print("Connecting to ChromaDB server...")
    storage_context = get_storage_context(get_vector_store(collection_name))

    print(f"Loading documents from {data_dir or 'the configured data directory'}...")
    documents = load_documents(data_dir)
    print(f"Loaded {len(documents)} document pages/files.")

    routed = route_documents(documents, type_overrides)
    nodes = chunk_documents(routed, Settings.embed_model)

    source_types = {
        doc.metadata.get("file_name", ""): source_type
        for source_type, docs in routed.items()
        for doc in docs
    }

    print(f"Embedding and saving {len(nodes)} total nodes to database...")
    VectorStoreIndex(nodes, storage_context=storage_context)

    return len(nodes), source_types
