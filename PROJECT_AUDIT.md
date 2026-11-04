# Project Audit: E-Commerce Customer Support Agentic RAG

**Audit Date**: November 2, 2026  
**Auditor**: Senior Python Developer & AI Engineer  
**Workspace**: `Ecommerce-Support-Agentic-RAG-main`  
**Execution Environment**: Windows 11 / Python 3.10.11 / PowerShell  

---

## 1. Executive Summary

The project is an AI-powered customer support application that combines:
1. A **Rasa NLU & Dialogue Core** chatbot service for conversational flow.
2. A **Flask REST API** implementing an **Agentic RAG Controller** (retriever with HyDE, augmenter, and LLM generator with tool calling and self-correction).
3. A **Streamlit Frontend** providing user chat, order tracking, and inventory status dashboards.
4. Supporting services: FakeStore API integration, mock order/product/policy data, Redis caching, and PostgreSQL persistence configuration.

While the conceptual architecture is well thought out, **the project cannot run out of the box in a local environment** due to missing dependency declarations, missing configuration/environment files, import path mismatches, missing sample knowledge base files, unhandled tool arguments, and hardcoded connection URLs.

---

## 2. Component Inventory & Architecture Breakdown

### 2.1 Backend Architecture (`api/`)
- **`api/app/__init__.py`**: Flask factory (`create_app`) registering `api_blueprint` at `/api`.
  - *Issues*: Uses `from app.routes import api_blueprint` which fails when run from root without `api` in `sys.path`. Does not initialize database or Redis.
- **`api/app/routes.py`**: Exposes:
  - `GET /api/orders/<order_id>` -> queries mock order database.
  - `GET /api/products/<product_name>/stock` -> queries mock product stock.
  - `POST /api/rag/query` -> runs `rag_controller.query()`.
  - Policy endpoints (`/returns/policy`, `/refunds/policy`, `/shipping`, `/payment/methods`, `/payment/policy`, `/warranty/<product_id>`).
  - *Issues*: Instantiates `PineconeVectorStore` and `OpenAIEmbeddings` at module load time. If `OPENAI_API_KEY` or `PINECONE_API_KEY` is not configured or network fails, importing `routes.py` crashes the entire backend. Missing health endpoint `/health`. Missing return endpoints expected by Rasa (`/api/returns/validate`, `/api/returns`, `/api/emails/send`).
- **`api/app/services/`**:
  - `order_service.py`: Lookups from `api.utils.mock_data.ORDERS`.
  - `product_service.py`: Lookups from `api.utils.mock_data.PRODUCTS`.
  - `return_refund_service.py`: Lookups from `api.utils.mock_data.POLICIES`.
  - `payment_shipping_service.py`: Lookups from `api.utils.mock_data.POLICIES`.
  - *Issues*: Use `from api.utils.mock_data import ...` which conflicts with imports when `api` is the root working directory.
- **`api/integrations/fakestore_client.py`**:
  - `get_product_info(product_id)`: Fetches product details via HTTP GET from `https://fakestoreapi.com/products/{product_id}`.
- **`api/utils/`**:
  - `mock_data.py`: In-memory dictionaries (`ORDERS`, `PRODUCTS`, `POLICIES`).
  - `redis_manager.py`: Incomplete snippet referencing undefined `Config.REDIS_HOST`.
  - `users.py`: Incomplete snippet attempting `from app import db` and Rasa `Action` definitions.
  - `helpers.py`: Empty file (0 bytes).

### 2.2 RAG & Agent Pipeline (`rag/`)
- **`rag/agents/agentic_controller.py`**:
  - Implements multi-hop loop (up to 3 hops), tool invocation, and self-correction (retries if confidence < 0.6).
- **`rag/agents/tools/tool_registry.py`**:
  - Exposes tools: `get_order_status` and `check_product_stock`.
  - *Issue*: Tool `check_product_stock` declares argument `product_name`, but `product_service.get_product_stock(product_id: str)` expects `product_id`. When LLM calls tool with `product_name="Laptop Pro"`, `func(**args)` raises `TypeError: get_product_stock() got an unexpected keyword argument 'product_name'`.
- **`rag/retrieval/vector_store.py`**:
  - Contains `InMemoryVectorStore` and `PineconeVectorStore`.
  - *Issues*: `InMemoryVectorStore` still invokes `OpenAIEmbeddings` inside `add_documents`. `InMemoryVectorStore.query()` does not return a `"score"` key, causing `augmenter.py` to calculate `avg_confidence = 0.0`, triggering infinite self-correction loops.
- **`rag/retrieval/retriever.py`**:
  - Implements `Retriever` with HyDE (`ChatOpenAI(model="gpt-4o-mini")`).
  - *Issues*: HyDE LLM is instantiated on class initialization without checking for API keys. MMR implementation tries to assign `search_type = "mmr"` on `BM25Retriever` (BM25 does not support vector MMR), and returns `Document` objects while `augmenter` expects dictionaries. Re-ranker passes raw list `results` to `ContextualCompressionRetriever(base_retriever=results)` which expects a retriever object.
- **`rag/augmentation/augmenter.py`**:
  - Formats retrieved chunks and calculates confidence score based on `score` in chunks.
  - *Issue*: Pinecone stores text under `metadata["text"]`, whereas augmenter reads `doc.get("text")`.
- **`rag/generation/generator.py`**:
  - Calls DeepSeek API via OpenAI SDK client.
  - *Critical Issue*: **Missing `import json`**! Line 40 calls `json.loads(tool_call.function.arguments)` and line 54 calls `json.dumps(result)`, which will raise `NameError: name 'json' is not defined` whenever tool calling is triggered.
  - Model name is hardcoded to `deepseek-r1`, which requires an active DeepSeek API key and base URL `https://api.deepseek.com/v1`.
- **`rag/ingestion/`**:
  - `loader.py`: Loads JSON, PDF, and CSV files from `source_dir`.
  - `chunker.py`: `DocumentChunker` using `RecursiveCharacterTextSplitter`. Expects `doc["text"]`.
  - `index_sample_docs.py`: Hardcoded path `data/documents/raw`. Missing raw document files in repository.
- **`rag/evaluation/`**:
  - `data/ecommerce.jsonl`: Golden evaluation dataset. Line 12 has a trailing comma causing invalid JSON parsing.
  - `evaluate_rag.py`: Looks for `rag/evaluation/data/my_ecommerce.jsonl` (which does not exist; actual file is `ecommerce.jsonl`). Requires `ragas` and `datasets`.

### 2.3 Dialogue Management (`rasa/`)
- Contains standard Rasa configuration: `domain.yml`, `config.yml`, `endpoints.yml`, `data/nlu.yml`, `data/rules.yml`, `data/stories.yml`.
- `rasa/actions/actions.py`:
  - `ActionGetOrderStatus`: calls `http://localhost:5000/api/orders/{order_id}`.
  - `ActionGetProductStock`: calls `http://localhost:5000/api/products/{product_name}/stock`.
  - `ActionInitiateReturn`: calls non-existent `/api/returns/validate`, `/api/returns`, `/api/emails/send`.
  - `ActionHandleComplexQuery`: calls DeepSeek directly with custom context.
  - `ActionRagQuery`: **Calls `http://localhost:8000/rag/query` instead of `http://localhost:5000/api/rag/query`**.
  - `domain.yml`: Does not register `action_rag_query` in `actions` list.

### 2.4 Frontend (`frontend/`)
- Streamlit application (`frontend/streamlit_app.py`).
- Interacts with Rasa endpoint (`http://localhost:5005/webhooks/rest/webhook`) and Flask API (`http://localhost:5000/api`).
- *Issues*:
  - Order Tracking input validates `len(order_id) == 12 and order_id.isalnum()`. Mock orders like `ORD-1001` fail this validation.
  - Expects `result.get('location')` and `delivery_date`, which `order_service` does not output.
  - No direct fallback to chat with Flask RAG service when Rasa is not running.

---

## 3. Query Execution Trace (End-to-End)

```
[User]
   │
   ├─► Streamlit UI (Port 8501)
   │     │
   │     ├─► [Order Tracking / Stock Check Form]
   │     │     │
   │     │     └─► Flask REST API (Port 5000)
   │     │           ├─► /api/orders/<id> -> mock_data.ORDERS
   │     │           └─► /api/products/<name>/stock -> mock_data.PRODUCTS
   │     │
   │     └─► [AI Assistant Chat]
   │           │
   │           └─► Rasa Server (Port 5005)
   │                 │
   │                 ├─► [Standard Intent] -> Rasa Action Server (Port 5055)
   │                 │                          └─► Flask API (Port 5000)
   │                 │
   │                 └─► [Complex / Knowledge Query]
   │                       │
   │                       └─► Rasa Action Server -> ActionRagQuery
   │                             │
   │                             └─► POST /api/rag/query
   │                                   │
   │                                   ▼
   │                            AgenticRAGController
   │                                   │
   │                                   ├─► Step 1: Retriever (HyDE + Vector Store)
   │                                   │     ├─ HyDE generates hypothetical doc (ChatOpenAI)
   │                                   │     ├─ Embeds query (text-embedding-3-large)
   │                                   │     └─ Vector search (Pinecone or InMemory)
   │                                   │
   │                                   ├─► Step 2: Augmenter
   │                                   │     └─ Formats context & calculates confidence
   │                                   │
   │                                   ├─► Step 3: Generator (DeepSeek-R1 / OpenAI API)
   │                                   │     └─ Generates answer OR invokes tool
   │                                   │
   │                                   ├─► Step 4: Tool Execution (if tool called)
   │                                   │     ├─ check_product_stock / get_order_status
   │                                   │     └─ Loops back for final answer synthesis
   │                                   │
   │                                   └─► Step 5: Self-Correction Loop
   │                                         └─ If confidence < 0.6: refines query & retries
```

---

## 4. Current Status Matrix: Working vs. Broken Features

| Feature / Subsystem | Status | Root Cause / Blocker |
|---|---|---|
| Flask App Launch | ❌ Broken | Root-level import errors (`app.routes`), module-level Pinecone & OpenAI initialization crashes if API keys are missing. |
| Health Check Endpoint | ❌ Missing | No `/health` or `/api/health` route exists. |
| In-Memory Vector Store | ⚠️ Incomplete | `add_documents` still depends on OpenAI; `query` lacks `score` attribute. |
| Pinecone Vector Store | ⚠️ Unconfigured | Requires active Pinecone cloud account, API key, and index `ecommerce-agentic-rag`. |
| Document Ingestion Pipeline | ❌ Broken | `data/documents/raw` directory is missing; `chunker.py` expects dicts but loader yields strings for PDFs. |
| Generator Tool Calling | ❌ Broken | `import json` missing in `rag/generation/generator.py`; argument mismatch (`product_name` vs `product_id`) in `tool_registry.py`. |
| Rasa Action Server | ❌ Broken | `ActionRagQuery` calls wrong port (`8000`), missing return endpoints in Flask. |
| Streamlit UI Chat | ⚠️ Blocked | Hardcoded to Rasa endpoint; crashes or hangs if Rasa is offline. |
| Streamlit Order Tracking | ❌ Broken | Regex/Length validation blocks valid mock order IDs (e.g. `ORD-1001`). |
| Database & Redis Persistence | ⚠️ Mock / Inactive | Models in `api/utils/users.py` are uninstantiated placeholders; Redis manager has undefined attributes. |
| Automated Tests (`tests/`) | ❌ Broken | `test_api_rag.py` imports non-existent FastAPI `router`; `test_rag.py` looks for non-existent folders and uses mismatched constructor params. |
| Docker Compose Setup | ❌ Broken | Docker not installed on host; missing `api/Dockerfile` and `frontend/Dockerfile`. |

---

## 5. Dependency & Environment Deficiencies

1. **`requirements.txt` issues**:
   - Includes `deepseek-sdk==0.1.0` (non-existent/unneeded package; code uses `openai.OpenAI`).
   - Pinning `rasa[transformers]==3.6.21` forces `pydantic<2.0`, `sqlalchemy<1.5`, `numpy<1.24`, conflicting with modern LangChain packages.
   - Missing explicit declarations for:
     - `langchain-openai`
     - `langchain-community`
     - `langchain-text-splitters`
   - Spacy wheel is hardcoded as an external wheel URL which can fail without wheel build tools.
2. **Missing Configuration**:
   - No `.env` or `.env.example` file.
   - Missing required credentials:
     - `OPENAI_API_KEY` (mandatory for OpenAI embeddings and HyDE).
     - `DEEPSEEK_API_KEY` (mandatory for DeepSeek generator).
     - `PINECONE_API_KEY` (optional if in-memory vector store is supported).
3. **Missing Files**:
   - `data/documents/raw/` containing sample policy PDFs/JSONs.
   - `api/Dockerfile`, `frontend/Dockerfile`, `rasa/actions/requirements.txt`.
   - `rag/evaluation/data/my_ecommerce.jsonl` (referenced by evaluation script).

---

## 6. Action Plan for Phase 2–Phase 8

1. **Phase 2 (Environment & Dependencies)**:
   - Clean up `requirements.txt` to enable smooth Windows local installation using Python 3.10.
   - Provide a working `.env.example` and template `.env`.
   - Create local Windows virtual environment setup instructions.
2. **Phase 3 (External Services & Fallbacks)**:
   - Provide clear instructions for obtaining required keys (`OPENAI_API_KEY`, `DEEPSEEK_API_KEY`, `PINECONE_API_KEY`).
   - Provide an offline/mock fallback mode for LLM and embeddings so the backend can run and pass all tests even without paid API keys.
3. **Phase 4 (Backend Remediation)**:
   - Fix all imports across `api/` and `rag/` to allow seamless execution from repository root.
   - Add `/health` endpoint to Flask.
   - Implement missing return endpoints (`/api/returns/validate`, `/api/returns`, `/api/emails/send`).
   - Add sample documentation files under `data/documents/` and fix loader/chunker format discrepancies.
   - Make vector store selection configurable (`Pinecone` vs `InMemoryVectorStore`).
4. **Phase 5 (Agent & Tools Remediation)**:
   - Fix `generator.py` missing `import json`.
   - Align tool schema and service parameters in `tool_registry.py` and `product_service.py`.
   - Fix retriever MMR and re-ranker issues.
5. **Phase 6 (Frontend Remediation)**:
   - Relax order ID validation in Streamlit to accept mock IDs (`ORD-1001`).
   - Add a direct RAG chat option in Streamlit so users can test the agent even without running the Rasa stack.
6. **Phase 7 & 8 (Execution & Verification)**:
   - Fix tests in `tests/test_rag.py` and `tests/test_api_rag.py`.
   - Verify health, order queries, stock queries, RAG pipeline, tool calling, and Streamlit UI.
   - Document all steps in `LOCAL_SETUP.md` and `TEST_RESULTS.md`.
