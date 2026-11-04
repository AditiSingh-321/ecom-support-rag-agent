"""
Chunker for semantic/sliding window chunking of documents using LangChain.
"""
from typing import List, Dict, Any, Union
from langchain_text_splitters import RecursiveCharacterTextSplitter

class DocumentChunker:
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""],  # Semantic separators: paragraphs, lines, sentences, words
            keep_separator=True
        )

    def chunk_text(self, text: str) -> List[str]:
        """Chunk text semantically with overlap."""
        if not text:
            return []
        return self.splitter.split_text(text)

    def chunk_docs(self, docs: List[Union[Dict[str, Any], str]]) -> List[Dict[str, Any]]:
        """Chunk multiple docs and add metadata."""
        chunked = []
        for idx, doc in enumerate(docs):
            if isinstance(doc, str):
                doc_text = doc
                source = "unknown"
                metadata = {}
                doc_id = idx
            elif isinstance(doc, dict):
                doc_text = doc.get("text", "") or doc.get("content", "") or str(doc)
                source = doc.get("source", "unknown")
                metadata = doc.get("metadata", {})
                doc_id = doc.get("doc_id", doc.get("id", idx))
            else:
                doc_text = str(doc)
                source = "unknown"
                metadata = {}
                doc_id = idx

            chunks = self.chunk_text(doc_text)
            for i, chunk in enumerate(chunks):
                chunked.append({
                    "doc_id": doc_id,
                    "chunk_id": i,
                    "text": chunk,
                    "total_chunks": len(chunks),
                    "source": source,
                    "metadata": {**metadata, "source": source}
                })
        return chunked
