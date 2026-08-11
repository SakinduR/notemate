import chromadb
from chromadb.errors import NotFoundError
from llama_index.core.storage.storage_context import StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore

from app.config import settings


def _chroma_client() -> chromadb.HttpClient:
    return chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)


def get_chroma_collection(collection_name: str | None = None):
    return _chroma_client().get_or_create_collection(collection_name or settings.chroma_collection)


def delete_collection(collection_name: str) -> None:
    """Best-effort delete -- a session that never had a document ingested
    never had a Chroma collection created for it, so "already gone" isn't
    an error here.
    """
    try:
        _chroma_client().delete_collection(collection_name)
    except NotFoundError:
        pass


def get_vector_store(collection_name: str | None = None) -> ChromaVectorStore:
    return ChromaVectorStore(chroma_collection=get_chroma_collection(collection_name))


def get_storage_context(vector_store: ChromaVectorStore | None = None) -> StorageContext:
    return StorageContext.from_defaults(vector_store=vector_store or get_vector_store())
