"""
Tool Registry: Define available tools with schema for LLM.
"""
from typing import Dict, Any, Callable
import json

try:
    from api.app.services.order_service import get_order_status
    from api.app.services.product_service import get_product_stock
except ImportError:
    from app.services.order_service import get_order_status
    from app.services.product_service import get_product_stock

class Tool:
    def __init__(self, name: str, func: Callable, description: str, parameters: Dict):
        self.name = name
        self.func = func
        self.description = description
        self.parameters = parameters

    def to_schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }

    def execute(self, args: Dict) -> Any:
        try:
            return self.func(**args)
        except TypeError:
            # Fallback if argument names differ slightly
            return self.func(*args.values())

# Define Tools
TOOLS = [
    Tool(
        name="get_order_status",
        func=get_order_status,
        description="Get current status of an order by order_id. Use when user asks about order tracking.",
        parameters={
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "The order ID, e.g. ORD-1001, ORD-1002, #123"}
            },
            "required": ["order_id"]
        }
    ),
    Tool(
        name="check_product_stock",
        func=get_product_stock,
        description="Check if a product is in stock by name or ID. Returns stock count and restock date.",
        parameters={
            "type": "object",
            "properties": {
                "product_name": {"type": "string", "description": "Name or ID of the product, e.g. Laptop Pro, Galaxy S21"}
            },
            "required": ["product_name"]
        }
    )
]

TOOL_REGISTRY = {tool.name: tool for tool in TOOLS}
