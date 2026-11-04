"""
Augmenter: Combines query + retrieved docs into LLM-ready prompt.
"""
from typing import List, Dict, Any

class RAGAugmenter:
    def __init__(self):
        self.system_prompt = (
            "You are an expert e-commerce customer support agent. "
            "Use ONLY the provided context to answer user's queries. "
            "If unsure, say 'I don't have enough information.' "
            "Cite sources using [Source: X] format."
        )

    def augment(self, query: str, docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not docs:
            return {
                "prompt": f"{self.system_prompt}\n\nUser: {query}\nAssistant: I don't have enough information to answer this.",
                "metadata": {"sources": [], "confidence": 0.0}
            }

        # Format context with source + text
        context_blocks = []
        total_score = 0.0
        for i, doc in enumerate(docs):
            meta = doc.get("metadata", {})
            text = (doc.get("text") or meta.get("text") or "").strip()
            source = meta.get("source") or doc.get("source") or "Document"
            score = float(doc.get("score", 0.75))
            total_score += score
            context_blocks.append(f"[Source {i+1}: {source}]\n{text}\n")

        context = "\n".join(context_blocks)
        avg_confidence = total_score / len(docs) if docs else 0.0

        prompt = f"""\
{self.system_prompt}

Context:
{context}

User: {query}
Assistant:"""

        metadata = {
            "sources": [
                {
                    "source": d.get("metadata", {}).get("source") or d.get("source", "Unknown"),
                    "score": round(float(d.get("score", 0.75)), 3)
                }
                for d in docs
            ],
            "confidence": round(avg_confidence, 3)
        }

        return {"prompt": prompt, "metadata": metadata}
