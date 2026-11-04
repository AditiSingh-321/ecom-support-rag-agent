# api/app/services/return_service.py
try:
    from api.utils.mock_data import POLICIES, ORDERS
except ImportError:
    from utils.mock_data import POLICIES, ORDERS

def get_return_policy(product_id: str = None) -> dict:
    """Return return policy. If product_id given, try product-specific."""
    base = POLICIES["return"]
    if product_id and product_id in POLICIES.get("products", {}):
        specific = POLICIES["products"][product_id].get("return", {})
        return {**base, **specific}
    return base

def get_refund_policy(product_id: str = None) -> dict:
    """Refund policy with dummy form link."""
    base = POLICIES["refund"]
    if product_id and product_id in POLICIES.get("products", {}):
        specific = POLICIES["products"][product_id].get("refund", {})
        return {**base, **specific}
    return base

def validate_return_eligibility(order_id: str) -> dict:
    """Validate if an order is eligible for return."""
    order = ORDERS.get(order_id)
    if not order:
        clean_id = order_id.strip().lstrip("#").upper()
        for k, v in ORDERS.items():
            if k.upper() == clean_id or k.upper().replace("-", "") == clean_id.replace("-", ""):
                order = v
                order_id = k
                break

    if not order:
        return {"eligible": False, "reason": "Order not found", "order_id": order_id}

    status = order.get("status", "").lower()
    if status == "delivered":
        return {"eligible": True, "reason": "Delivered within 30 days", "order_id": order_id}
    elif status in ["shipped", "processing"]:
        return {"eligible": False, "reason": f"Order is currently {status}, not yet delivered.", "order_id": order_id}
    else:
        return {"eligible": False, "reason": f"Order status is {status}", "order_id": order_id}
