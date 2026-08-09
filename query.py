import chromadb
from llama_index.core import VectorStoreIndex, Settings
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.storage.storage_context import StorageContext
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.vector_stores import MetadataFilters, ExactMatchFilter

# 1. Load the exact same embedding model used for ingestion
print("Loading embedding model...")
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
Settings.llm = None # We are just testing retrieval, no LLM needed yet

# 2. Connect to your existing local database
print("Connecting to ChromaDB...")
db = chromadb.PersistentClient(path="./chroma_db")
chroma_collection = db.get_or_create_collection("course_materials")
vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)

# Load the index from the vector store
index = VectorStoreIndex.from_vector_store(
    vector_store, storage_context=storage_context
)

# 3. Set up Metadata Filters (The Core Differentiator)
# This forces the system to ONLY look at chunks tagged as 'lecture_slides'.
# You can change this to 'reference_book' or 'past_paper' to test different modes.
target_source = "lecture_slides"
filters = MetadataFilters(
    filters=[ExactMatchFilter(key="source_type", value=target_source)]
)

# Build the retriever
retriever = index.as_retriever(
    similarity_top_k=3, # Bring back the top 3 most relevant chunks
    filters=filters
)

# 4. Execute a Test Query
# Change this string to a concept that actually exists in your test PDF!
query_text = "What are the benefits of using the cloud for software development?" 

print(f"\n🔍 Searching for: '{query_text}'")
print(f"📂 Filtering strictly by: {target_source}\n")

# This fetches the raw chunks of text (Nodes) from the database
retrieved_nodes = retriever.retrieve(query_text)

# 5. Display the Results
if not retrieved_nodes:
    print("No relevant chunks found. Try changing the query or the filter.")
else:
    for i, node in enumerate(retrieved_nodes):
        print(f"--- Result {i+1} ---")
        print(f"Similarity Score: {node.score:.3f} (Higher is better)")
        print(f"Source Tag: {node.metadata.get('source_type')}")
        print(f"Extracted Text:\n{node.text}\n")