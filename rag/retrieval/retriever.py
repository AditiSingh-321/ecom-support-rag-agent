"""
Retriever with semantic search, reranker, MMR, and HyDE support.
"""
from typing import List, Dict, Any, Optional, Callable
import os
from rag.retrieval.vector_store import VectorStore, _deterministic_local_embed
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class Retriever:
    def __init__(
        self,
        vector_store: VectorStore,
        embed_fn: Optional[Any] = None,
        rerank_fn: Optional[Callable] = None,
        hyde_llm: Optional[Any] = None,
        hyde_fn: Optional[Callable[[str], str]] = None
    ):
        self.vector_store = vector_store

        # Embed function setup
        if embed_fn is not None:
            self.embed_fn = embed_fn
        elif OPENAI_API_KEY and OPENAI_API_KEY.strip() and not OPENAI_API_KEY.startswith("your_"):
            try:
                from langchain_openai import OpenAIEmbeddings
                self.embed_fn = OpenAIEmbeddings(model="text-embedding-3-large", api_key=OPENAI_API_KEY)
            except Exception:
                self.embed_fn = None
        else:
            self.embed_fn = None

        self.rerank_fn = rerank_fn
        self.hyde_fn = hyde_fn

        # HyDE LLM setup
        if hyde_llm is not None:
            self.hyde_llm = hyde_llm
        elif hyde_fn is not None:
            self.hyde_llm = None
        elif OPENAI_API_KEY and OPENAI_API_KEY.strip() and not OPENAI_API_KEY.startswith("your_"):
            try:
                from langchain_openai import ChatOpenAI
                self.hyde_llm = ChatOpenAI(model="gpt-4o-mini", api_key=OPENAI_API_KEY)
            except Exception:
                self.hyde_llm = None
        else:
            self.hyde_llm = None

    def _embed(self, text: str) -> List[float]:
        if hasattr(self.embed_fn, "embed_query"):
            return self.embed_fn.embed_query(text)
        elif callable(self.embed_fn):
            return self.embed_fn(text)
        else:
            return _deterministic_local_embed(text)

    def hyde_query(self, query: str) -> str:
        """Generate hypothetical document for HyDE Retrieval."""
        if self.hyde_fn is not None:
            try:
                return self.hyde_fn(query)
            except Exception:
                return query
        if self.hyde_llm is not None:
            try:
                hypo_prompt = f"Write a detailed hypothetical answer to: {query}"
                resp = self.hyde_llm.invoke(hypo_prompt)
                return getattr(resp, "content", str(resp))
            except Exception:
                return query
        return query

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        use_hyde: bool = False,
        use_mmr: bool = False,
        use_rerank: bool = False
    ) -> List[Dict[str, Any]]:
        query_text = self.hyde_query(query) if use_hyde else query
        query_emb = self._embed(query_text)

        # Base retrieval
        fetch_k = top_k * 3 if (use_mmr or use_rerank) else top_k
        results = self.vector_store.query(query_emb, top_k=fetch_k)

        # Standardize items
        standardized = []
        for r in results:
            meta = r.get("metadata", {})
            text_val = r.get("text") or meta.get("text", "")
            standardized.append({
                "id": str(r.get("id", "")),
                "score": float(r.get("score", 0.75)),
                "text": text_val,
                "metadata": {**meta, "text": text_val, "source": meta.get("source", "doc")}
            })

        if not standardized:
            return []

        # Simple diversity re-ranking if MMR requested
        if use_mmr and len(standardized) > top_k:
            selected = [standardized[0]]
            for item in standardized[1:]:
                if len(selected) >= top_k:
                    break
                # Ensure diversity by not picking chunks with duplicate text/source
                if not any(item["text"][:60] in s["text"] for s in selected):
                    selected.append(item)
            results = selected
        else:
            results = standardized[:top_k]

        return results
