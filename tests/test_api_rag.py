"""
Integration test: test Flask API endpoints including health, orders, products, and RAG.
"""
import unittest
import json
from api.app import create_app

class TestApiEndpoints(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def test_root_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get("status"), "healthy")

    def test_api_health(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get("status"), "healthy")

    def test_order_status_endpoint(self):
        response = self.client.get("/api/orders/ORD-1001")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("status", data)
        self.assertEqual(data["status"], "Shipped")

    def test_product_stock_endpoint(self):
        response = self.client.get("/api/products/Laptop Pro/stock")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("stock", data)
        self.assertEqual(data["stock"], 8)

    def test_return_policy_endpoint(self):
        response = self.client.get("/api/returns/policy")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("days", data)

    def test_return_validate_endpoint(self):
        response = self.client.post("/api/returns/validate", json={"order_id": "ORD-1003"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("eligible", data)

    def test_rag_query_endpoint(self):
        payload = {"query": "What is the return policy?"}
        response = self.client.post("/api/rag/query", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("answer", data)
        self.assertTrue(len(data["answer"]) > 0)

if __name__ == "__main__":
    unittest.main()
