from llama_index.core import SimpleDirectoryReader
from llama_index.core.schema import Document
from llama_index.readers.file import PyMuPDFReader

from app.config import settings


def load_documents(data_dir: str | None = None) -> list[Document]:
    pdf_extractor = {".pdf": PyMuPDFReader()}
    return SimpleDirectoryReader(
        data_dir or settings.data_dir,
        file_extractor=pdf_extractor,
    ).load_data()
