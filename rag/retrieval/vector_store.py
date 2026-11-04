"""
Vector store adapter interface and Pinecone/in-memory implementations with OpenAI embeddings.
"""
from typing import List, Dict, Any, Optional
import os
import hashlib
import numpy as np
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "ecommerce-agentic-rag")

def _deterministic_local_embed(text: str, dim: int = 128) -> List[float]:
    """Lightweight offline embedding for local development without OpenAI API key."""
    vec = np.zeros(dim, dtype=float)
    tokens = text.lower().split()
    if not tokens:
        return vec.tolist()
    for token in tokens:
        idx = int(hashlib.md5(token.encode('utf-8')).hexdigest(), 16) % dim
        vec[idx] += 1.0
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()

class VectorStore:
    def add_documents(self, docs: List[Dict[str, Any]]):
        raise NotImplementedError
    def query(self, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        raise NotImplementedError

class InMemoryVectorStore(VectorStore):
    def __init__(self, embed_fn=None):
        self.vectors = []  # List of dicts: {"id": str, "embedding": list, "metadata": dict, "text": str}
        self.embed_fn = embed_fn

    def _get_embedding(self, text: str) -> List[float]:
        if self.embed_fn:
            return self.embed_fn.embed_query(text)
        if OPENAI_API_KEY and OPENAI_API_KEY.strip() and not OPENAI_API_KEY.startswith("your_"):
            try:
                from langchain_openai import OpenAIEmbeddings
                embeddings = OpenAIEmbeddings(model="text-embedding-3-large", api_key=OPENAI_API_KEY)
                return embeddings.embed_query(text)
            except Exception:
                pass
        return _deterministic_local_embed(text)

    def add_documents(self, docs: List[Dict[str, Any]]):
        for doc in docs:
            embedding = doc.get("embedding")
            if embedding is None:
                text_content = doc.get("text", "")
                embedding = self._get_embedding(text_content)
            
            metadata = doc.get("metadata", {})
            text_val = doc.get("text", "")
            if "text" not in metadata and text_val:
                metadata["text"] = text_val

            self.vectors.append({
                "id": str(doc.get("id", len(self.vectors))),
                "embedding": embedding,
                "metadata": metadata,
                "text": text_val
            })

    def query(self, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        if not self.vectors:
            return []
        
        q_emb = np.array(query_embedding, dtype=float)
        q_norm = np.linalg.norm(q_emb)
        if q_norm == 0:
            q_norm = 1e-8

        scored = []
        for v in self.vectors:
            v_emb = np.array(v["embedding"], dtype=float)
            v_norm = np.linalg.norm(v_emb)
            if v_norm == 0:
                v_norm = 1e-8
            
            # Pad or truncate dimensions if mismatch
            if len(q_emb) != len(v_emb):
                min_len = min(len(q_emb), len(v_emb))
                score = float(np.dot(q_emb[:min_len], v_emb[:min_len]) / (q_norm * v_norm))
            else:
                score = float(np.dot(q_emb, v_emb) / (q_norm * v_norm))
            
            score = max(0.0, min(1.0, (score + 1.0) / 2.0))  # normalize to [0, 1]
            scored.append((score, v))

        scored.sort(reverse=True, key=lambda x: x[0])
        return [
            {
                "id": v["id"],
                "score": round(score, 4),
                "metadata": v.get("metadata", {}),
                "text": v.get("text", "")
            }
            for score, v in scored[:top_k]
        ]

class PineconeVectorStore(VectorStore):
    def __init__(self, index_name: str = PINECONE_INDEX_NAME):
        self.index_name = index_name
        self.index = None
        if PINECONE_API_KEY and PINECONE_API_KEY.strip() and not PINECONE_API_KEY.startswith("your_"):
            try:
                from pinecone import Pinecone
                pc = Pinecone(api_key=PINECONE_API_KEY)
                self.index = pc.Index(index_name)
            except Exception as e:
                print(f"Warning: Pinecone initialization failed: {e}")

    def add_documents(self, docs: List[Dict[str, Any]]):
        if not self.index:
            raise RuntimeError("Pinecone index is not initialized.")
        from langchain_openai import OpenAIEmbeddings
        embeddings = OpenAIEmbeddings(model="text-embedding-3-large", api_key=OPENAI_API_KEY)
        vectors = [
            {
                "id": str(doc["id"]),
                "values": doc.get("embedding") or embeddings.embed_query(doc["text"]),
                "metadata": {"text": doc["text"], **doc.get("metadata", {})}
            }
            for doc in docs
        ]
        self.index.upsert(vectors=vectors)

    def query(self, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        if not self.index:
            raise RuntimeError("Pinecone index is not initialized.")
        results = self.index.query(vector=query_embedding, top_k=top_k, include_metadata=True)
        return [
            {
                "id": match["id"],
                "score": float(match.get("score", 0.0)),
                "metadata": match.get("metadata", {}),
                "text": match.get("metadata", {}).get("text", "")
            }
            for match in results.get("matches", [])
        ]
