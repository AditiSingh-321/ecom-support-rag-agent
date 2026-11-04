"""
Loader for documents (PDF, CSV, JSON) for RAG ingestion pipeline.
"""
import os
import json
import csv
from typing import List, Dict, Any

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

class DocumentLoader:
    def __init__(self, source_dir: str):
        self.source_dir = source_dir

    def _ensure_dir(self) -> bool:
        return os.path.exists(self.source_dir)

    def load_json(self) -> List[Dict[str, Any]]:
        """Load all JSON files from source_dir."""
        docs = []
        if not self._ensure_dir():
            return docs

        for fname in os.listdir(self.source_dir):
            if fname.lower().endswith('.json'):
                fpath = os.path.join(self.source_dir, fname)
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            for item in data:
                                if isinstance(item, dict):
                                    if "source" not in item:
                                        item["source"] = fname
                                    docs.append(item)
                        elif isinstance(data, dict):
                            if "source" not in data:
                                data["source"] = fname
                            docs.append(data)
                except Exception as e:
                    print(f"Error loading {fpath}: {e}")
        return docs

    def load_pdf(self) -> List[Dict[str, Any]]:
        """Load and extract text from all PDFs in source_dir."""
        docs = []
        if not self._ensure_dir() or PdfReader is None:
            return docs

        for fname in os.listdir(self.source_dir):
            if fname.lower().endswith('.pdf'):
                fpath = os.path.join(self.source_dir, fname)
                try:
                    reader = PdfReader(fpath)
                    text = "\n".join(page.extract_text() or "" for page in reader.pages)
                    docs.append({
                        "text": text,
                        "source": fname,
                        "metadata": {"source": fname, "pages": len(reader.pages)}
                    })
                except Exception as e:
                    print(f"Error loading {fpath}: {e}")
        return docs

    def load_csv(self) -> List[Dict[str, Any]]:
        """Load all CSV files from source_dir."""
        docs = []
        if not self._ensure_dir():
            return docs

        for fname in os.listdir(self.source_dir):
            if fname.lower().endswith('.csv'):
                fpath = os.path.join(self.source_dir, fname)
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            text_content = " | ".join(f"{k}: {v}" for k, v in row.items())
                            docs.append({
                                "text": text_content,
                                "source": fname,
                                "metadata": dict(row)
                            })
                except Exception as e:
                    print(f"Error loading {fpath}: {e}")
        return docs

    def load_all(self) -> List[Dict[str, Any]]:
        """Unified loader that merges JSON, PDF, and CSV."""
        return self.load_json() + self.load_pdf() + self.load_csv()
