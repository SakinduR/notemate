import os
import chromadb
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.storage.storage_context import StorageContext
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.node_parser import SentenceSplitter

# 1. Setup Local Embedding Model
# This converts your text into vector math. BAAI/bge-small-en-v1.5 is fast, lightweight, and great for local testing.
print("Loading embedding model...")
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")

# We don't need the LLM just yet for ingestion, so we turn it off to save resources
Settings.llm = None 

# 2. Setup the Chunking Strategy (Node Parser)
# This splits your PDF into chunks of 512 tokens. 
# The overlap of 50 tokens ensures we don't accidentally cut a definition (like a regex rule) in half.
Settings.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)

# 3. Initialize the Local Vector Database
# This creates a folder called 'chroma_db' on your machine to save the data permanently.
print("Initializing ChromaDB...")
db = chromadb.PersistentClient(path="./chroma_db")
chroma_collection = db.get_or_create_collection("course_materials")
vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)

# 4. Load the Documents
# This reads any PDFs or text files in your 'data' folder.
print("Loading documents from /data folder...")
documents = SimpleDirectoryReader("./data").load_data()
print(f"Loaded {len(documents)} document pages/files.")

# 5. Process and Store
# This is where the magic happens: it chunks the text, embeds it, and saves it to ChromaDB.
print("Chunking, embedding, and saving to database... This might take a minute.")
index = VectorStoreIndex.from_documents(
    documents, storage_context=storage_context
)

print("✅ Phase 1 Complete! Your data is now searchable math.")