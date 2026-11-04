try:
    from api.utils.mock_data import ORDERS
except ImportError:
    from utils.mock_data import ORDERS

def get_order_status(order_id: str = None, **kwargs) -> dict:
    """Get order status by order ID with fallback search."""
    oid = order_id or kwargs.get("id") or ""
    if not oid:
        return {"status": "Not found", "eta": None, "product_id": None}

    order = ORDERS.get(oid)
    found_key = oid

    if not order:
        clean_id = oid.strip().lstrip("#").upper()
        for k, v in ORDERS.items():
            k_clean = k.upper().replace("-", "")
            if (k.upper() == clean_id or 
                k_clean == clean_id or 
                clean_id in k.upper() or
                k.upper() in clean_id):
                order = v
                found_key = k
                break

    if not order:
        # Also provide a default mock status for demo orders like #123
        if "123" in oid:
            return {
                "order_id": oid,
                "status": "Shipped",
                "eta": "2025-11-08",
                "delivery_date": "2025-11-08",
                "last_updated": "2025-11-02",
                "product_id": "PROD-001",
                "carrier": "DHL",
                "location": {"lat": 40.7128, "lng": -74.0060}
            }
        return {
            "order_id": oid,
            "status": "Not found",
            "eta": None,
            "delivery_date": "N/A",
            "last_updated": "N/A",
            "product_id": None
        }

    return {
        "order_id": found_key,
        "status": order.get("status", "Not found"),
        "eta": order.get("eta"),
        "delivery_date": order.get("eta", "N/A"),
        "last_updated": "2025-11-02",
        "product_id": order.get("product_id"),
        "user_email": order.get("user_email"),
        "location": {"lat": 37.7749, "lng": -122.4194}
    }
