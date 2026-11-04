"""
Comprehensive test script for Phase 5 agent capabilities:
1. Product information queries.
2. Product search.
3. Order tracking.
4. Return-policy questions.
5. Inventory lookup.
6. Multi-turn conversations.
7. Tool calling.
8. Retrieval retries.
9. Error handling.
"""
import unittest
from rag.retrieval.vector_store import InMemoryVectorStore
from rag.retrieval.retriever import Retriever
from rag.agents.agentic_controller import AgenticRAGController
from rag.ingestion.loader import DocumentLoader
from rag.ingestion.chunker import DocumentChunker
from api.app.services.order_service import get_order_status
from api.app.services.product_service import get_product_stock
from api.app.services.return_refund_service import get_return_policy, validate_return_eligibility
from api.integrations.fakestore_client import get_product_info

class TestAgentCapabilities(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Setup in-memory store populated with documents
        cls.store = InMemoryVectorStore()
        loader = DocumentLoader("data/documents")
        docs = loader.load_all()
        chunker = DocumentChunker()
        chunks = chunker.chunk_docs(docs)
        cls.store.add_documents(chunks)
        cls.retriever = Retriever(vector_store=cls.store)
        cls.controller = AgenticRAGController(cls.retriever)

    # 1. Product information queries
    def test_01_product_info_query(self):
        result = self.controller.query("What are the specifications of the Laptop Pro?")
        self.assertIn("answer", result)
        self.assertTrue(len(result["answer"]) > 0)
        self.assertTrue(result["confidence"] >= 0.0)

    # 2. Product search via FakeStore integration
    def test_02_product_search(self):
        try:
            prod = get_product_info(1)
            self.assertIn("title", prod)
            self.assertIn("price", prod)
        except Exception:
            # FakeStore API might be unreachable if offline; test fallback mock
            stock = get_product_stock("Laptop Pro")
            self.assertIn("stock", stock)

    # 3. Order tracking
    def test_03_order_tracking(self):
        status = get_order_status("ORD-1001")
        self.assertEqual(status["status"], "Shipped")
        self.assertEqual(status["order_id"], "ORD-1001")
        
        # Test query through controller
        result = self.controller.query("Where is my order ORD-1001?")
        self.assertIn("answer", result)
        self.assertTrue(any(t["tool"] == "get_order_status" for t in result.get("tool_calls", [])))

    # 4. Return-policy questions
    def test_04_return_policy_questions(self):
        policy = get_return_policy()
        self.assertEqual(policy["days"], 30)
        
        result = self.controller.query("What is the return policy?")
        self.assertIn("30 days", result["answer"])

    # 5. Inventory lookup
    def test_05_inventory_lookup(self):
        stock = get_product_stock("Galaxy S21")
        self.assertEqual(stock["stock"], 0)
        
        # Test query through controller
        result = self.controller.query("Check stock for Galaxy S21")
        self.assertIn("answer", result)
        self.assertTrue(any(t["tool"] == "check_product_stock" for t in result.get("tool_calls", [])))

    # 6. Multi-turn conversation capability
    def test_06_multi_turn_simulation(self):
        # Turn 1: user checks return policy
        turn1 = self.controller.query("Can I return an item?")
        self.assertIn("return", turn1["answer"].lower())
        
        # Turn 2: user asks to validate specific delivered order
        turn2 = validate_return_eligibility("ORD-1003")
        self.assertTrue(turn2["eligible"])

    # 7. Tool calling
    def test_07_tool_calling(self):
        result = self.controller.query("Please check stock for Noise-Cancelling Headphones")
        tool_names = [t["tool"] for t in result.get("tool_calls", [])]
        self.assertIn("check_product_stock", tool_names)

    # 8. Retrieval retries and self-correction
    def test_08_retrieval_retries(self):
        # A vague or low confidence query should execute without crashing
        result = self.controller.query("xyz mysterious random query")
        self.assertIn("answer", result)
        self.assertIn("retrieval_retries", result)

    # 9. Error handling
    def test_09_error_handling(self):
        # Non-existent order
        non_existent = get_order_status("NON_EXISTENT_9999")
        self.assertEqual(non_existent["status"], "Not found")

        # Non-existent product
        non_prod = get_product_stock("Quantum Levitator")
        self.assertEqual(non_prod["stock"], "Not found")

if __name__ == "__main__":
    unittest.main()
