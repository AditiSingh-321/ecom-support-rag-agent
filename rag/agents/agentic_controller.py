"""
Agentic RAG Controller: Full pipeline with:
- Self-correction (low confidence)
- Tool calling (multi-hop)
- RAG augmentation
"""
from rag.retrieval.retriever import Retriever
from rag.augmentation.augmenter import RAGAugmenter
from rag.generation.generator import RAGGenerator
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class AgenticRAGController:
    def __init__(self, retriever: Retriever):
        self.retriever = retriever
        self.augmenter = RAGAugmenter()
        self.generator = RAGGenerator()
        self.max_hops = 3
        self.max_retries = 2
        self.confidence_threshold = 0.6

    def query(self, user_query: str) -> Dict[str, Any]:
        messages: List[Dict] = [{"role": "user", "content": user_query}]
        tool_calls_history = []
        current_query = user_query
        docs = []

        for hop in range(self.max_hops):
            retry_count = 0
            while retry_count <= self.max_retries:
                # Step 1: Retrieve
                docs = self.retriever.retrieve(
                    current_query, top_k=5, use_hyde=False, use_mmr=True
                )

                # Step 2: Augment
                augmented = self.augmenter.augment(current_query, docs)
                messages[0]["content"] = augmented["prompt"]

                # Step 3: Generate with tool calling
                result = self.generator.generate(messages, use_tools=True)

                # Step 4: Tool Calling
                if result.get("tool_calls"):
                    tool_calls_history.extend(result["tool_calls"])
                    # If generator already produced a full synthesized answer with the tool call
                    if result.get("response") and not result.get("error"):
                        confidence = max(0.9, augmented["metadata"]["confidence"])
                        return {
                            "answer": result["response"],
                            "sources": augmented["metadata"]["sources"],
                            "confidence": confidence,
                            "tool_calls": tool_calls_history,
                            "hops": hop + 1,
                            "retrieval_retries": retry_count,
                            "retrieved_docs": docs
                        }

                    last_tool = result["tool_calls"][-1]
                    current_query = f"Using tool result: {last_tool['output']}, answer: {user_query}"
                    break  # Tool called → proceed to next hop

                # Step 5: Self-Correction (Low Confidence)
                confidence = augmented["metadata"]["confidence"]
                if confidence < self.confidence_threshold and retry_count < self.max_retries:
                    logger.info(f"Low confidence ({confidence:.2f}), retry {retry_count + 1}")
                    context_snippet = docs[0].get("text", "")[:200] if docs else ""
                    current_query = (
                        f"Rephrase and improve: '{user_query}' "
                        f"using partial context: {context_snippet}"
                    )
                    retry_count += 1
                    continue
                else:
                    # Final answer
                    return {
                        "answer": result.get("response", ""),
                        "sources": augmented["metadata"]["sources"],
                        "confidence": confidence,
                        "tool_calls": tool_calls_history,
                        "hops": hop + 1,
                        "retrieval_retries": retry_count,
                        "retrieved_docs": docs
                    }

        return {
            "answer": "I couldn't find a reliable resolution to your query this time. Please contact customer support directly.",
            "sources": [],
            "confidence": 0.0,
            "tool_calls": tool_calls_history,
            "hops": self.max_hops,
            "retrieval_retries": 0,
            "retrieved_docs": docs
        }
