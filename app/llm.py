from llama_index.llms.google_genai import GoogleGenAI

from app.config import settings


def get_llm() -> GoogleGenAI:
    if not settings.google_api_key:
        raise ValueError("Missing GOOGLE_API_KEY in .env file")
    return GoogleGenAI(model=settings.gemini_model, temperature=0)
