"""
Generator: Calls DeepSeek for final response using augmented prompt.
Supports tool calling with LLM, and local deterministic fallback when API keys are not present.
"""
import os
import json
import re
from typing import Dict, Any, List
from dotenv import load_dotenv
from rag.agents.tools.tool_registry import TOOL_REGISTRY

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_BASE = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
USE_MOCK_LLM = os.getenv("USE_MOCK_LLM", "false").lower() == "true" or not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY.startswith("your_")

class RAGGenerator:
    def __init__(self):
        self.use_mock = USE_MOCK_LLM
        self.tools = [tool.to_schema() for tool in TOOL_REGISTRY.values()]
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

        if not self.use_mock:
            try:
                from openai import OpenAI
                self.client = OpenAI(
                    base_url=DEEPSEEK_API_BASE,
                    api_key=DEEPSEEK_API_KEY
                )
            except Exception as e:
                print(f"Warning: Failed to initialize OpenAI client for DeepSeek: {e}. Falling back to mock generator.")
                self.use_mock = True
        else:
            self.client = None

    def _extract_user_query(self, messages: List[Dict]) -> str:
        """Extract user question from augmented messages."""
        for msg in reversed(messages):
            content = msg.get("content", "")
            if "User:" in content and "Assistant:" in content:
                return content.split("User:")[-1].split("Assistant:")[0].strip()
            if msg.get("role") == "user":
                return content
        return messages[-1].get("content", "")

    def _mock_generate(self, messages: List[Dict], use_tools: bool = True) -> Dict[str, Any]:
        """Local deterministic fallback for offline testing and local execution without paid API keys."""
        user_query = self._extract_user_query(messages)
        user_lower = user_query.lower()

        # 1. Check for order queries in user query
        order_match = re.search(r"(?:order|ord)[- #]*([a-zA-Z0-9-]+)", user_lower, re.IGNORECASE)
        if use_tools and ("track" in user_lower or "where" in user_lower or "status" in user_lower or "order" in user_lower):
            if order_match or "#" in user_lower or "ord-" in user_lower:
                order_id = order_match.group(1).strip() if order_match else "ORD-1001"
                if order_id.isdigit():
                    order_id = f"ORD-{order_id}" if int(order_id) > 1000 else f"#{order_id}"
                tool = TOOL_REGISTRY["get_order_status"]
                tool_args = {"order_id": order_id}
                result = tool.execute(tool_args)
                return {
                    "response": f"Your order {result.get('order_id', order_id)} is currently {result.get('status', 'Processing')}. Expected delivery: {result.get('delivery_date') or result.get('eta', 'soon')}.",
                    "tool_calls": [{"tool": "get_order_status", "input": tool_args, "output": result}]
                }

        # 2. Check for product stock queries in user query
        if use_tools and ("stock" in user_lower or "in stock" in user_lower or "available" in user_lower or "availability" in user_lower or "how many" in user_lower):
            p_name = "Laptop Pro"
            if "galaxy" in user_lower or "s21" in user_lower:
                p_name = "Galaxy S21"
            elif "backpack" in user_lower or "fjallraven" in user_lower:
                p_name = "Fjallraven Backpack"
            elif "headphone" in user_lower:
                p_name = "Noise-Cancelling Headphones"
            elif "laptop" in user_lower:
                p_name = "Laptop Pro"

            tool = TOOL_REGISTRY["check_product_stock"]
            tool_args = {"product_name": p_name}
            result = tool.execute(tool_args)
            stock_count = result.get("stock", "Not found")
            if stock_count == 0:
                answer = f"{result.get('product_name', p_name)} is currently out of stock. Restock expected on {result.get('restock_date', 'soon')}."
            else:
                answer = f"{result.get('product_name', p_name)} is in stock with {stock_count} units available."
            return {
                "response": answer,
                "tool_calls": [{"tool": "check_product_stock", "input": tool_args, "output": result}]
            }

        # 3. Policy answers based on context & query
        if "return" in user_lower:
            return {
                "response": "Customers can return items within 30 days of purchase for a full refund or exchange if unopened and in original packaging. Electronics must be in sealed boxes.",
                "tool_calls": []
            }
        if "refund" in user_lower:
            return {
                "response": "Refunds are processed within 5 to 10 business days after the returned item is received and inspected at our fulfillment center.",
                "tool_calls": []
            }
        if "shipping" in user_lower or "ship" in user_lower:
            return {
                "response": "Standard shipping takes 5-7 business days (free on domestic orders over $50). Expedited delivery takes 2-3 business days. International shipping is available to over 50 countries.",
                "tool_calls": []
            }
        if "payment" in user_lower or "pay" in user_lower:
            return {
                "response": "We accept major credit cards (Visa, MasterCard, Amex), PayPal, Apple Pay, and Google Pay with 256-bit SSL encryption.",
                "tool_calls": []
            }
        if "warranty" in user_lower:
            return {
                "response": "Our products come with manufacturer warranties: Laptop Pro includes a 2-year warranty plus 1 year accidental damage, while others include a standard 1-year warranty.",
                "tool_calls": []
            }
        if "spec" in user_lower or "laptop" in user_lower or "backpack" in user_lower:
            return {
                "response": "Laptop Pro features a 15.6-inch 4K OLED display, 32GB RAM, 1TB NVMe SSD, and Intel Core i7 processor with 2-year manufacturer warranty.",
                "tool_calls": []
            }

        return {
            "response": "Thank you for reaching out to customer support. Based on our policy documents, please let us know your specific order number or product name so we can assist you directly.",
            "tool_calls": []
        }

    def generate(self, messages: List[Dict], use_tools: bool = True) -> Dict[str, Any]:
        if self.use_mock or not self.client:
            return self._mock_generate(messages, use_tools=use_tools)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=500,
                tools=self.tools if use_tools else None,
                tool_choice="auto" if use_tools else None
            )

            msg = response.choices[0].message

            # Handle tool calls
            if getattr(msg, "tool_calls", None):
                tool_results = []
                for tool_call in msg.tool_calls:
                    func_name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)
                    tool = TOOL_REGISTRY.get(func_name)
                    if tool:
                        result = tool.execute(args)
                    else:
                        result = {"error": f"Tool {func_name} not found"}

                    tool_results.append({
                        "tool": func_name,
                        "input": args,
                        "output": result
                    })
                    # Add tool result to messages
                    messages.append(msg)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": func_name,
                        "content": json.dumps(result)
                    })

                # Final generation
                final_resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=300
                )
                return {
                    "response": final_resp.choices[0].message.content,
                    "tool_calls": tool_results
                }
            else:
                return {"response": msg.content, "tool_calls": []}

        except Exception as e:
            print(f"DeepSeek generation exception: {e}. Using mock fallback.")
            fallback = self._mock_generate(messages, use_tools=use_tools)
            fallback["error"] = str(e)
            return fallback
