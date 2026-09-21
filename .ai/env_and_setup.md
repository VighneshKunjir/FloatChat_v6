# FloatChat: Local Environment & Setup Guide

## 1. Prerequisites
- **Node.js:** v20.x or v22.x LTS (`node -v`, `npm -v`).
- **Python:** v3.11 or v3.12 (`python3 -v`).
- **Virtual Environment:** `venv` or `conda`.
- **Docker & Docker Compose:** (Optional, only required if running PostgreSQL container).

---

## 2. Environment Variables Specification

Create a `.env` file at the project root based on `.env.example`:

```bash
cp .env.example .env
```

### Complete Variable Table

| Variable Name | Environment | Required? | Default Value | Description |
| :--- | :--- | :---: | :--- | :--- |
| `PORT` | Node / Vite | Yes | `3000` | Port for the frontend dev server and reverse proxy |
| `NODE_ENV` | Node | No | `development` | Runtime environment (`development` or `production`) |
| `GEMINI_API_KEY` | Server-side only | No | `""` | Google Gemini API key for grounded conversational dialogue. If omitted, automatic offline analytical synthesis fallback is active. |
| `DATABASE_URL` | Python backend | No | `sqlite:///./backend/data/floatchat.db` | Connection string for SQLite or PostgreSQL |
| `BACKEND_PORT` | Python backend | No | `8000` | Port for FastAPI Uvicorn server |
| `CORS_ORIGINS` | Python backend | No | `http://localhost:3000` | Comma-separated allowed frontend origins |
| `MODEL_WEIGHTS_PATH` | Python backend | No | `backend/app/ml/artifacts/model_weights.pt` | Path to serialized PyTorch model weights |

---

## 3. Step-by-Step Local Setup

### Step A: Clone & Install Frontend Dependencies
```bash
# 1. Install Node dependencies
npm install

# 2. Verify TypeScript build and linting
npm run lint
```

### Step B: Setup Python ML Backend
```bash
# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install backend scientific & ML packages
pip install -r backend/requirements.txt

# 3. Seed SQLite database with Arabian Sea floats
python backend/scripts/seed_db.py --db-url "sqlite:///./backend/data/floatchat.db"
```

### Step C: Launch Development Services

#### Option 1: Current All-in-One Dev Server (Node + Vite Bridge)
```bash
npm run dev
# App is accessible at: http://localhost:3000
```

#### Option 2: Production Dual-Process Mode (FastAPI + Vite)
In Terminal 1 (Python Backend):
```bash
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --app-dir backend
```

In Terminal 2 (React Frontend):
```bash
npm run dev
# Open browser at: http://localhost:3000
```

---

## 4. Docker Compose Setup (PostgreSQL + Full Stack)

If you prefer to run with PostgreSQL 16:

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: floatchat_db
    environment:
      POSTGRES_DB: floatchat
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgrespassword
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    container_name: floatchat_backend
    environment:
      DATABASE_URL: postgresql://postgres:postgrespassword@postgres:5432/floatchat
      GEMINI_API_KEY: ${GEMINI_API_KEY}
    ports:
      - "8000:8000"
    depends_on:
      - postgres

  frontend:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: floatchat_frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend

volumes:
  pgdata:
```

Command:
```bash
docker-compose up -d --build
```

---

## 5. Troubleshooting & Diagnostics

- **Issue: `vite: not found` or module errors**
  - *Fix:* Run `npm install`.
- **Issue: `GEMINI_API_KEY` missing**
  - *Fix:* FloatChat automatically switches to its offline deterministic oceanographic synthesis engine. All forecasts, XAI attributions, and chat explanations remain 100% operational without an API key.
- **Issue: KaTeX formula rendering error**
  - *Fix:* Verify `katex/dist/katex.min.css` is included in `index.html`.
