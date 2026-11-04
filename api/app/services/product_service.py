try:
    from api.utils.mock_data import PRODUCTS
except ImportError:
    from utils.mock_data import PRODUCTS

def get_product_stock(product_name: str = None, product_id: str = None, **kwargs) -> dict:
    """
    Get product stock availability by product name or product ID.
    Accepts product_name, product_id, or positional argument.
    """
    query = product_name or product_id or kwargs.get("name") or ""
    if not query:
        return {"stock": "Not found", "restock_date": "N/A", "product_name": "Unknown"}

    # 1. Exact match by key
    if query in PRODUCTS:
        p = PRODUCTS[query]
        return {
            "product_name": query,
            "product_id": p.get("product_id"),
            "stock": p.get("stock", 0),
            "restock_date": p.get("restock_date", "N/A")
        }

    # 2. Case-insensitive key match or substring match
    q_lower = query.lower()
    for name, p in PRODUCTS.items():
        if name.lower() == q_lower or q_lower in name.lower() or p.get("product_id", "").lower() == q_lower:
            return {
                "product_name": name,
                "product_id": p.get("product_id"),
                "stock": p.get("stock", 0),
                "restock_date": p.get("restock_date", "N/A")
            }

    return {
        "product_name": query,
        "stock": "Not found",
        "restock_date": "N/A"
    }
