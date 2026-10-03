# Local Development Setup Guide

## 1. Environment Preparation
```bash
git clone https://github.com/NISHAKAR06/threshold-ai-governance.git
cd threshold-ai-governance

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Or .venv\Scripts\activate on Windows

# Install dependencies including dev tools
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov
```

## 2. Environment Configuration
Ensure your `.env` contains valid configuration keys:
```ini
ENVIRONMENT=development
LOG_LEVEL=INFO
DATABASE_URL=sqlite:///./THRESHOLD.db
VECTOR_STORE_PATH=./data/vector_store
CHUNKS_PATH=./data/chunks
GEMINI_API_KEY=mock-key-or-valid-key
LLM_PROVIDER=mock  # Set to gemini for live Google GenAI integration
EMBEDDING_PROVIDER=mock  # Set to gemini for live embeddings
```

## 3. Launch Development Server
```bash
python -m uvicorn app.main:app --reload --port 8000
```
Open your browser at `http://localhost:8000`.
