import os
import requests

FAKESTORE_API_URL = os.getenv("FAKESTORE_API_BASE", "https://fakestoreapi.com").rstrip("/")

def get_product_info(product_id):
    """Fetch product details from FakeStore API with timeout and graceful fallback."""
    try:
        response = requests.get(f"{FAKESTORE_API_URL}/products/{product_id}", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {
            "id": product_id,
            "title": f"Product #{product_id}",
            "price": 99.99,
            "description": "Product details temporarily unavailable offline.",
            "error": str(e)
        }
