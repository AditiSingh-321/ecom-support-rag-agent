"""
Script to index sample docs into vector store (in-memory or Pinecone).
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from rag.ingestion.loader import DocumentLoader
from rag.ingestion.chunker import DocumentChunker
from rag.retrieval.vector_store import InMemoryVectorStore, PineconeVectorStore

if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent.parent
    source_dir = repo_root / "data" / "documents"
    if not source_dir.exists():
        source_dir = repo_root / "data" / "documents" / "raw"

    print(f"Loading documents from {source_dir}...")
    loader = DocumentLoader(source_dir=str(source_dir))
    docs = loader.load_all()
    chunker = DocumentChunker(chunk_size=512, chunk_overlap=50)
    chunks = chunker.chunk_docs(docs)
    
    # Assign IDs and metadata
    for chunk in chunks:
        chunk["id"] = f"doc{chunk['doc_id']}_chunk{chunk['chunk_id']}"
        chunk["metadata"] = {"source": chunk.get("source", "ecommerce_doc")}

    vstore_type = os.getenv("VECTOR_STORE_TYPE", "in_memory").lower()
    pinecone_key = os.getenv("PINECONE_API_KEY", "")

    if vstore_type == "pinecone" and pinecone_key and not pinecone_key.startswith("your_"):
        store = PineconeVectorStore(index_name=os.getenv("PINECONE_INDEX_NAME", "ecommerce-agentic-rag"))
        print(f"Indexing {len(chunks)} chunks to Pinecone...")
    else:
        store = InMemoryVectorStore()
        print(f"Indexing {len(chunks)} chunks to InMemoryVectorStore...")

    store.add_documents(chunks)
    print(f"Successfully indexed {len(chunks)} chunks.")

    # Example test query
    query = "backpack specs"
    print(f"Testing retrieval for '{query}'...")
    from rag.retrieval.vector_store import _deterministic_local_embed
    query_emb = _deterministic_local_embed(query)
    results = store.query(query_emb, top_k=2)
    print(f"Found {len(results)} matching results:")
    for r in results:
        print(f" - [{r.get('score')}] {r.get('text')[:100]}...")
