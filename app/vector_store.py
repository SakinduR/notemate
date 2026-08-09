import chromadb
from llama_index.core.storage.storage_context import StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore

from app.config import settings


def get_chroma_collection():
    client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
    return client.get_or_create_collection(settings.chroma_collection)


def get_vector_store() -> ChromaVectorStore:
    return ChromaVectorStore(chroma_collection=get_chroma_collection())


def get_storage_context(vector_store: ChromaVectorStore | None = None) -> StorageContext:
    return StorageContext.from_defaults(vector_store=vector_store or get_vector_store())
