# Deployment Guide — Threshold AI Governance

## 1. Prerequisites
- Python 3.10+
- Docker & Docker Compose (optional for containerized deployments)
- SQLite (default embedded storage) or PostgreSQL
- 4GB+ RAM recommended for ChromaDB vector operations

## 2. Local Environment Setup
```bash
# Clone the repository
git clone https://github.com/NISHAKAR06/threshold-ai-governance.git
cd threshold-ai-governance

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env  # Or configure .env

# Run database migrations
python -m alembic upgrade head

# Start application server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 3. Docker Deployment
```bash
# Build and run with Docker Compose
docker-compose up --build -d

# Verify container health
curl http://localhost:8000/health
curl http://localhost:8000/ready
```
The application will be accessible at `http://localhost:8000`.
