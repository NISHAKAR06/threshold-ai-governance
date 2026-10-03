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

Docker Compose expects `SECRET_KEY`, `JWT_SECRET`, and `POSTGRES_PASSWORD` to be supplied externally. To use its PostgreSQL profile, set both runtime and sync migration URLs to the `threshold-db` hostname; no password or production secret is baked into the image or Compose file.

Docker daemon validation is pending in the current environment because Docker Desktop is not running. The commands below are the deployment procedure to run once a daemon is available; they are not recorded here as completed validation.
```bash
# Build and run with Docker Compose
docker-compose up --build -d

# Verify container health
curl http://localhost:8000/health
curl http://localhost:8000/ready
```
The application will be accessible at `http://localhost:8000`.

## Production environment

Set `SECRET_KEY`, `JWT_SECRET`, `DATABASE_URL`, `CORS_ORIGINS`, and `TRUSTED_HOSTS` in the deployment environment or an uncommitted `.env` file. Set `GEMINI_API_KEY` only when Gemini is enabled. Compose requires secret and PostgreSQL-password variables rather than providing insecure defaults.

The Docker image runs as non-root `appuser`. It uses `/health` for liveness; use `/ready` for dependency-aware readiness checks.

GitHub Actions runs compilation, lint error checks, unit tests, integration tests, the evaluation smoke test, and a production `docker build`. CI does not inject production credentials; deployment secrets must be configured in the deployment environment or repository secrets when a deployment workflow is added.
