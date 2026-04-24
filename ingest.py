import os
import chromadb
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.storage.storage_context import StorageContext
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.node_parser import SemanticSplitterNodeParser, SentenceSplitter
from llama_index.core.schema import TextNode

# 1. Setup Local Embedding Model
print("Loading embedding model...")
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
Settings.llm = None 

# 2. Initialize the Local Vector Database
print("Initializing ChromaDB...")
db = chromadb.PersistentClient(path="./chroma_db")
chroma_collection = db.get_or_create_collection("course_materials")
vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)

# 3. Load Documents
print("Loading documents from /data folder...")
documents = SimpleDirectoryReader("./data").load_data()

# 4. Document Routing & Metadata Tagging
slide_docs = []
book_docs = []
paper_docs = []
general_docs = []

print("Routing documents based on file names...")
for doc in documents:
    file_name = doc.metadata.get('file_name', '').lower()
    
    # Exclude basic file stats from the math embeddings, keep our custom tags
    doc.excluded_embed_metadata_keys = [
        'file_name', 'file_path', 'file_type', 'file_size', 
        'creation_date', 'last_modified_date', 'last_accessed_date'
    ]
    
    if 'slides' in file_name:
        doc.metadata['source_type'] = 'lecture_slides'
        slide_docs.append(doc)
    elif 'reference' in file_name:
        doc.metadata['source_type'] = 'reference_book'
        book_docs.append(doc)
    elif 'past paper' in file_name:
        doc.metadata['source_type'] = 'past_paper'
        paper_docs.append(doc)
    else:
        doc.metadata['source_type'] = 'general_notes'
        general_docs.append(doc)

# 5. Execute Specific Chunking Strategies
all_nodes = [] # This will hold all our finalized chunks

# Strategy A: Semantic Chunking for Reference Books
if book_docs:
    print(f"Applying Semantic Chunking to {len(book_docs)} reference book pages...")
    semantic_parser = SemanticSplitterNodeParser(
        buffer_size=1, 
        breakpoint_percentile_threshold=95, 
        embed_model=Settings.embed_model
    )
    all_nodes.extend(semantic_parser.get_nodes_from_documents(book_docs))

# Strategy B: Structural/Smaller Chunking for Lecture Slides
# Slides are sparse. We use a standard splitter but with smaller chunks 
# to keep individual bullet points tightly grouped.
if slide_docs:
    print(f"Applying Structural Chunking to {len(slide_docs)} slide pages...")
    slide_parser = SentenceSplitter(chunk_size=256, chunk_overlap=20)
    all_nodes.extend(slide_parser.get_nodes_from_documents(slide_docs))

# Strategy C: Agentic Chunking for Past Papers
if paper_docs:
    print(f"Applying Agentic Extraction to {len(paper_docs)} past paper pages...")
    for doc in paper_docs:
        # TODO in Phase 3: Send doc.text to an LLM API (like Groq or Gemini Free Tier)
        # and ask it to return a JSON array of individual questions.
        
        # For now, we simulate the LLM's output by manually creating a Node.
        # This proves the architecture works without needing an API key yet.
        simulated_llm_extracted_question = "Question 1: Explain the advantages of QPSK modulation."
        
        # Create a custom node manually
        node = TextNode(
            text=simulated_llm_extracted_question,
            metadata={
                **doc.metadata, # Inherit the 'past_paper' tag
                "extracted_by_agent": True,
                "estimated_topic": "Modulation Techniques" # Simulated LLM tagging
            }
        )
        all_nodes.append(node)

# Catch any unclassified documents
if general_docs:
    general_parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)
    all_nodes.extend(general_parser.get_nodes_from_documents(general_docs))

# 6. Process and Store
# Notice we use `from_nodes` instead of `from_documents` now, because we pre-chunked everything!
print(f"Embedding and saving {len(all_nodes)} total nodes to database...")
index = VectorStoreIndex(
    all_nodes, storage_context=storage_context
)

print("✅ Phase 1 Complete! Hybrid processing pipeline executed.")