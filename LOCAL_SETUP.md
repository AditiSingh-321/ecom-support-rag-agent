# Local Setup Guide: E-Commerce Customer Support Agentic RAG

This guide provides step-by-step instructions to configure, run, and test the application on **Windows** using **PowerShell**.

---

## Prerequisites

- **Windows 10 / 11**
- **Python 3.10+** (verified on Python 3.10.11)
- **PowerShell** (or Windows Terminal)
- *(Optional)* Docker Desktop if running Option B

---

## Option A: Run Without Docker (Recommended Local Execution)

### Step 1: Open PowerShell and Navigate to Workspace
```powershell
cd <path-to-repository>
```

### Step 2: Create and Activate Virtual Environment
```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1
```
*(If PowerShell displays an ExecutionPolicy error, run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` once).*

### Step 3: Install Project Dependencies
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy the template configuration file:
```powershell
Copy-Item .env.example .env
```
Key configuration settings in `.env`:
- `VECTOR_STORE_TYPE`: Set to `in_memory` (default) for local zero-cloud execution, or `pinecone` if you have Pinecone credentials.
- `USE_MOCK_LLM`: Set to `true` (or leave empty `DEEPSEEK_API_KEY`) to run offline without paid API keys.
- `OPENAI_API_KEY`: *(Optional)* Add your key if using OpenAI embeddings and HyDE.
- `DEEPSEEK_API_KEY`: *(Optional)* Add your key if using DeepSeek-R1 cloud generation.

### Step 5: Ingest Knowledge Base Documents
Index the sample policy and product warranty documents into the vector database:
```powershell
python -m rag.retrieval.index_sample_docs
```

### Step 6: Run Automated Tests
Verify all 23 unit and integration tests pass:
```powershell
python -m unittest discover tests
```

### Step 7: Start the Flask Backend Server
In PowerShell Terminal 1:
```powershell
.\venv\Scripts\Activate.ps1
python api/app/__init__.py
```
- **Backend URL**: `http://localhost:5000`
- **Health Check**: `http://localhost:5000/health` or `http://localhost:5000/api/health`

### Step 8: Start the Streamlit Frontend
In PowerShell Terminal 2:
```powershell
cd <path-to-repository>
.\venv\Scripts\Activate.ps1
streamlit run frontend/streamlit_app.py
```
- **Streamlit Web UI**: `http://localhost:8501`

---

## Option B: Run with Docker Compose

If you have **Docker Desktop** installed and running on Windows:

### Step 1: Configure Environment
Ensure `.env` exists and contains your keys:
```powershell
Copy-Item .env.example .env
```

### Step 2: Build and Run Services
```powershell
docker-compose up --build
```

### Services Started:
- **Flask REST API**: `http://localhost:5000`
- **Streamlit Frontend**: `http://localhost:8501`
- **Redis Cache**: `localhost:6379`
- **Rasa Server**: `http://localhost:5005`
- **Rasa Action Server**: `http://localhost:5055`

---

## Quick Verification Commands

From another PowerShell terminal, test the running backend endpoints:

```powershell
# 1. Health Check
Invoke-RestMethod -Uri "http://localhost:5000/api/health"

# 2. Check Order Status
Invoke-RestMethod -Uri "http://localhost:5000/api/orders/ORD-1001"

# 3. Check Product Stock
Invoke-RestMethod -Uri "http://localhost:5000/api/products/Laptop%20Pro/stock"

# 4. Check Return Policy
Invoke-RestMethod -Uri "http://localhost:5000/api/returns/policy"

# 5. Full Agentic RAG Query (with tool invocation)
Invoke-RestMethod -Uri "http://localhost:5000/api/rag/query" -Method Post -Body '{"query":"Where is my order ORD-1001?"}' -ContentType 'application/json'
```
