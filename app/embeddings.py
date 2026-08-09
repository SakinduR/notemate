from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from app.config import settings


def get_embed_model() -> HuggingFaceEmbedding:
    return HuggingFaceEmbedding(model_name=settings.embed_model_name)
