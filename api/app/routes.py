import os
import sys
import uuid
from pathlib import Path
from flask import Blueprint, jsonify, request
from dotenv import load_dotenv

# Ensure root and api are on sys.path
repo_root = Path(__file__).resolve().parent.parent.parent
api_dir = Path(__file__).resolve().parent.parent
for p in [str(repo_root), str(api_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

load_dotenv()

try:
    from app.services.order_service import get_order_status
    from app.services.product_service import get_product_stock
    from app.services.return_refund_service import (
        get_return_policy,
        get_refund_policy,
        validate_return_eligibility
    )
    from app.services.payment_shipping_service import (
        get_shipping_info,
        get_payment_methods,
        get_payment_policy,
        get_warranty_info
    )
except ImportError:
    from api.app.services.order_service import get_order_status
    from api.app.services.product_service import get_product_stock
    from api.app.services.return_refund_service import (
        get_return_policy,
        get_refund_policy,
        validate_return_eligibility
    )
    from api.app.services.payment_shipping_service import (
        get_shipping_info,
        get_payment_methods,
        get_payment_policy,
        get_warranty_info
    )

from rag.retrieval.vector_store import PineconeVectorStore, InMemoryVectorStore
from rag.retrieval.retriever import Retriever
from rag.agents.agentic_controller import AgenticRAGController
from rag.ingestion.loader import DocumentLoader
from rag.ingestion.chunker import DocumentChunker

api_blueprint = Blueprint('api', __name__)

# === Singleton Lazy Controller Initialization ===
_rag_controller = None

def get_rag_controller():
    global _rag_controller
    if _rag_controller is not None:
        return _rag_controller

    vstore_type = os.getenv("VECTOR_STORE_TYPE", "in_memory").lower()
    pinecone_key = os.getenv("PINECONE_API_KEY", "")

    if vstore_type == "pinecone" and pinecone_key and not pinecone_key.startswith("your_"):
        try:
            vector_store = PineconeVectorStore(index_name=os.getenv("PINECONE_INDEX_NAME", "ecommerce-agentic-rag"))
        except Exception as e:
            print(f"Warning: Failed to load Pinecone store: {e}. Falling back to InMemoryVectorStore.")
            vector_store = InMemoryVectorStore()
    else:
        vector_store = InMemoryVectorStore()

    # If in-memory, auto-load knowledge base documents on startup
    if isinstance(vector_store, InMemoryVectorStore):
        docs_dir = repo_root / "data" / "documents"
        if docs_dir.exists():
            loader = DocumentLoader(str(docs_dir))
            docs = loader.load_all()
            chunker = DocumentChunker(chunk_size=512, chunk_overlap=50)
            chunks = chunker.chunk_docs(docs)
            vector_store.add_documents(chunks)
            print(f"Loaded {len(chunks)} knowledge chunks into in-memory vector store.")

    retriever = Retriever(vector_store=vector_store)
    _rag_controller = AgenticRAGController(retriever)
    return _rag_controller

# === Health Endpoint ===
@api_blueprint.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "service": "ecommerce-api",
        "vector_store": os.getenv("VECTOR_STORE_TYPE", "in_memory")
    }), 200

# === Core Business Endpoints ===
@api_blueprint.route('/orders/<order_id>', methods=['GET'])
def order_status(order_id):
    """Get order status by order ID"""
    status_info = get_order_status(order_id)
    return jsonify(status_info), 200

@api_blueprint.route('/products/<product_name>/stock', methods=['GET'])
def product_stock(product_name):
    """Get product stock availability"""
    stock_info = get_product_stock(product_name=product_name)
    return jsonify(stock_info), 200

# === Returns & Refunds Workflow Endpoints (used by Rasa & UI) ===
@api_blueprint.route('/returns/validate', methods=['POST'])
def return_validate():
    """Validate return eligibility for an order."""
    data = request.get_json() or {}
    order_id = data.get("order_id", "")
    result = validate_return_eligibility(order_id)
    return jsonify(result), 200

@api_blueprint.route('/returns', methods=['POST'])
def create_return():
    """Create a new return request."""
    data = request.get_json() or {}
    order_id = data.get("order_id", "")
    user_email = data.get("user_email", "")
    return_id = f"RET-{uuid.uuid4().hex[:8].upper()}"
    return jsonify({
        "return_id": return_id,
        "order_id": order_id,
        "user_email": user_email,
        "status": "Initiated",
        "message": f"Return {return_id} successfully registered."
    }), 201

@api_blueprint.route('/emails/send', methods=['POST'])
def send_email():
    """Simulate sending email confirmation."""
    data = request.get_json() or {}
    return jsonify({
        "status": "sent",
        "to": data.get("to"),
        "subject": data.get("subject")
    }), 200

# === Agentic RAG Endpoint ===
@api_blueprint.route('/rag/query', methods=['POST'])
def rag_query():
    """Full Agentic RAG: retrieval + tools + generation"""
    data = request.get_json()
    if not data or "query" not in data:
        return jsonify({"error": "Query is required"}), 400

    query = data["query"]
    try:
        controller = get_rag_controller()
        result = controller.query(query)
        return jsonify({
            "answer": result["answer"],
            "sources": result.get("sources", []),
            "confidence": result.get("confidence", 0.0),
            "tool_calls": result.get("tool_calls", []),
            "hops": result.get("hops", 1),
            "retrieval_retries": result.get("retrieval_retries", 0)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === RAG Policy Endpoints ===
@api_blueprint.route('/returns/policy', methods=['GET'])
def return_policy():
    product_id = request.args.get('product_id')
    return jsonify(get_return_policy(product_id)), 200

@api_blueprint.route('/refunds/policy', methods=['GET'])
def refund_policy():
    product_id = request.args.get('product_id')
    return jsonify(get_refund_policy(product_id)), 200

@api_blueprint.route('/shipping', methods=['GET'])
def shipping():
    return jsonify(get_shipping_info()), 200

@api_blueprint.route('/payment/methods', methods=['GET'])
def payment_methods():
    return jsonify(get_payment_methods()), 200

@api_blueprint.route('/payment/policy', methods=['GET'])
def payment_policy():
    return jsonify(get_payment_policy()), 200

@api_blueprint.route('/warranty/<product_id>', methods=['GET'])
def warranty(product_id):
    return jsonify(get_warranty_info(product_id)), 200
