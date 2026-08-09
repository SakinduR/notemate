from llama_index.core import Settings, VectorStoreIndex

from app.chunking import chunk_documents, route_documents
from app.embeddings import get_embed_model
from app.loaders import load_documents
from app.vector_store import get_storage_context


def run_ingestion(data_dir: str | None = None, type_overrides: dict[str, str] | None = None) -> int:
    print("Loading embedding model...")
    Settings.embed_model = get_embed_model()
    Settings.llm = None

    print("Connecting to ChromaDB server...")
    storage_context = get_storage_context()

    print(f"Loading documents from {data_dir or 'the configured data directory'}...")
    documents = load_documents(data_dir)
    print(f"Loaded {len(documents)} document pages/files.")

    routed = route_documents(documents, type_overrides)
    nodes = chunk_documents(routed, Settings.embed_model)

    print(f"Embedding and saving {len(nodes)} total nodes to database...")
    VectorStoreIndex(nodes, storage_context=storage_context)

    return len(nodes)
