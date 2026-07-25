# PaperForge

[![PaperForge CI](https://github.com/StarDeep18/PaperForge/actions/workflows/ci.yml/badge.svg)](https://github.com/StarDeep18/PaperForge/actions/workflows/ci.yml)
[![CodeQL Security Scan](https://github.com/StarDeep18/PaperForge/actions/workflows/codeql.yml/badge.svg)](https://github.com/StarDeep18/PaperForge/actions/workflows/codeql.yml)
[![Backend Tests](https://img.shields.io/badge/pytest-98%20passed-success?logo=pytest)](https://github.com/StarDeep18/PaperForge/actions)
[![Docker Image](https://img.shields.io/badge/docker-multi--stage-blue?logo=docker)](https://github.com/StarDeep18/PaperForge/pkgs/container/paperforge-server)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**AI-Powered Research Workspace**

PaperForge helps researchers, students, and professionals understand, organize, compare, and synthesize research papers using Retrieval-Augmented Generation (RAG).

## Features

- 📄 **Upload & Parse** — Upload PDFs, DOCX, and text files with intelligent parsing
- 🗂️ **Collections** — Organize papers into named collections
- 💬 **Chat with Papers** — Ask questions about one or multiple papers
- 📝 **Citation-Aware Answers** — Every response includes source citations
- 🔍 **Semantic Search** — Find relevant content across your library
- 📊 **Paper Comparison** — Compare methodologies, findings, and conclusions
- 📚 **Literature Reviews** — Auto-generate literature review drafts
- 🧠 **Research Gaps** — Identify gaps and opportunities
- 📋 **Study Tools** — Generate notes, flashcards, and quizzes

---

## Architecture & Codebase Design

PaperForge follows **Clean Architecture** to maintain provider-independence, testability, and scalability.

```
   Presentation Layer (FastAPI Routes / React UI)
             ↓
   Application Layer (Use Cases: Upload, ProcessDocument)
             ↓
   Domain Service Layer (RetrievalService, VectorStoreService, EmbeddingService)
        ↙         ↘
   Domain Interfaces (VectorStore, EmbeddingProvider, CollectionManager)
        ↖         ↗
   Infrastructure Layer (ChromaVectorStore, GeminiEmbeddingProvider, Mock Providers)
```

### Key Modules Implemented

1. **Embedding Layer**:
   - **`EmbeddingProvider` (ABC)**: Abstract interface decoupling embedding generation from external vendors.
   - **`GeminiEmbeddingProvider`**: Concrete adapter utilizing LangChain and Google Gemini APIs.
   - **`MockEmbeddingProvider`**: Local offline testing adapter.
   - **`EmbeddingService`**: Manages validation limits, concurrency semaphores, and batch partitioning.

2. **Vector Store Layer**:
   - **`VectorStore` (ABC)**: Abstract interface isolating database drivers. Includes compatibility adapters to support legacy callers (e.g. `RAGChain` search).
   - **`ChromaVectorStore`**: Integrates with ChromaDB, maps database output arrays to clean domain results, and computes cosine similarity scores from L2/IP distances.
   - **`CollectionManager` (ABC)**: Isolated interface managing collection lifecycles (creation, deletion, stats) distinct from vector indexing.
   - **`VectorStoreService`**: Coordinates duplicates check, NaN checks, vector dimension checks, and write batching.

3. **Retrieval Layer**:
   - **`RetrievalService`**: Orchestrates the multi-stage grounding context retrieval pipeline:
     1. **Generate Embedding**: Generates the vector representation of the query.
     2. **Vector Search**: Queries similarity records using the extensible `MetadataFilter`.
     3. **Duplicate Removal**: Filters duplicate chunk IDs and semantically similar vector matches (cosine threshold).
     4. **Parent Merge Consolidation**: Groups adjacent child chunks pointing to a common parent, replacing them with the continuous parent context to improve readability.
     5. **Token Budgeting**: Packages chunks within the configured context window limit using character ratio estimators.
     6. **Retrieval Inspector**: Produces detailed diagnostic logs and rankings to power debugging panels.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS, shadcn/ui |
| **Backend** | Python, FastAPI |
| **AI** | LangChain, Google Gemini API, Sentence Transformers |
| **Vector DB** | ChromaDB (swappable to Qdrant/Pinecone) |
| **Database** | SQLite (migratable to PostgreSQL) |
| **Document Processing** | PyMuPDF, python-docx |

---

## Quick Start

### Prerequisites

- Node.js 20+
- Python 3.11+
- Google API Key (for Gemini)

### Setup

```bash
# Clone and configure
cp .env.example .env
# Edit .env with your GOOGLE_API_KEY

# Backend Setup
cd server
python -m venv .venv
.venv\Scripts\activate  # Windows (or source .venv/bin/activate on Unix)
pip install -r requirements.txt
python -m app.main

# Frontend Setup (new terminal)
cd client
npm install
npm run dev
```


---

## Authentication & Token Refresh Strategy

PaperForge leverages Firebase Authentication for client-side identity management and backend token verification.

### Token Lifecycle & Silent Refresh

```mermaid
sequenceDiagram
    autonumber
    participant User as User / Browser Client
    participant Firebase as Firebase Auth SDK
    participant Axios as Axios API Client
    participant Backend as FastAPI Backend

    User->>Firebase: 1. Sign In (Email / Password or Provider)
    Firebase-->>User: 2. Return Credentials + ID Token (short-lived) + Refresh Token
    User->>Axios: 3. Perform App Action / API Call
    Axios->>Firebase: 4. Check Token Expiration (Silent Refresh if expired)
    Firebase-->>Axios: 5. Return Valid / Refreshed ID Token
    Axios->>Backend: 6. HTTP Request (Authorization: Bearer <ID_Token>)
    Backend->>Backend: 7. Verify Token via Firebase Admin SDK (or mock parser in dev)
    Backend-->>Axios: 8. Return Resource Data Payload
```

1. **Firebase**: User authenticates with Firebase Auth.
2. **ID Token**: Short-lived JWT generated by Firebase.
3. **Refresh Token**: Stored securely by the Firebase client SDK.
4. **Silent Refresh**: Axios interceptors request a fresh ID token transparently before sending requests.
5. **Axios**: Attaches current ID token to `Authorization: Bearer` request headers.
6. **FastAPI**: Validates token claims on every API route via `CurrentUser` dependency.

---

## Database Migration Workflow

Database schema evolution is managed explicitly through **Alembic** rather than startup runtime schema mutations.

### Contributor Workflow

```
Create migration  ──>  Review migration  ──>  Apply migration  ──>  Run tests  ──>  Deploy
```

1. **Create Migration**: Generate a new revision script after modifying SQLAlchemy ORM models.
   ```bash
   .venv\Scripts\alembic revision --autogenerate -m "describe_schema_change"
   ```
2. **Review Migration**: Inspect the generated file under `alembic/versions/` to verify table DDL statements.
3. **Apply Migration**: Execute schema changes cleanly using the helper CLI script.
   ```bash
   .venv\Scripts\python migrate.py upgrade head
   ```
4. **Run Tests**: Run test suite to verify data integrity and repository query contracts.
5. **Deploy**: Run `migrate.py upgrade head` in production deployment pipelines before launching app workers.

---

## Health Check & Diagnostics

PaperForge exposes system health check probes for container readiness/liveness, Kubernetes deployments, and infrastructure monitors.

- **Liveness Probe**: `GET /health/live` — Returns `200 OK` (`{"status": "live"}`) if process is active.
- **Readiness Probe**: `GET /health/ready` — Returns `200 OK` (`{"status": "ready"}`) when DB, Firebase, and Chroma connection checks pass (or `503 Service Unavailable` if degraded).
- **System Health**: `GET /health` — General diagnostic status payload.

**Sample Response (`/health/ready`)**:
```json
{
  "status": "ready",
  "database": "connected",
  "firebase": "configured",
  "vector_store": "ready",
  "version": "1.0.0"
}
```

---

## Production Docker Architecture & Deployment

PaperForge is fully containerized using multi-stage Docker builds and Docker Compose profiles, supporting local development, staging against PostgreSQL, and production cloud/Kubernetes deployments.

### Target Architecture

```
                  DEVELOPMENT PROFILE (`--profile dev`)
                    Internet
                        │
                        ▼
            Nginx Reverse Proxy / SPA (Port 80)
                        │
        ┌───────────────┴───────────────┐
        ▼                               ▼
 React Static Build (SPA)         FastAPI Backend
                                        │
                           ┌────────────┴─────────────┐
                           ▼                          ▼
                     SQLite (File)            Chroma Vector DB

------------------------------------------------------------------

                  PRODUCTION PROFILE (`--profile prod`)
                    Internet
                        │
                        ▼
            Nginx Reverse Proxy / SPA (Port 80)
                        │
        ┌───────────────┴───────────────┐
        ▼                               ▼
 React Static Build (SPA)         FastAPI Backend (Gunicorn)
                                        │
                           ┌────────────┴─────────────┐
                           ▼                          ▼
                   PostgreSQL Container       Chroma Vector DB
```

### Startup Order & Dependency Flow

Docker Compose enforces strict startup ordering and health-gated readiness:

```
PostgreSQL Container (prod only) ──┐
                                  ├──> FastAPI Backend ──> Health Probe (/health/ready) ──> Nginx Proxy
Chroma Vector DB Container ────────┘
```

1. **Database & Vector Store**: `postgres` (in production) and `chromadb` start first and initialize listening sockets.
2. **FastAPI Backend**: `server` waits for `postgres` and `chromadb` to pass internal healthchecks before initializing database tables and model layers.
3. **Health Check Gate**: Compose monitors `GET /health/ready`. Once the backend reports 200 OK, the Nginx client container starts.
4. **Nginx Reverse Proxy**: `client` routes incoming user HTTP traffic to the verified healthy backend.

### Managed & External Database Compatibility

The backend uses standard SQLAlchemy async drivers (`sqlite+aiosqlite` or `postgresql+asyncpg`). For production cloud deployments, simply update `DATABASE_URL` in `.env` to point to any managed PostgreSQL provider without changing application code:
```env
# Managed PostgreSQL (Neon / Supabase / AWS RDS / GCP Cloud SQL)
DATABASE_URL=postgresql+asyncpg://user:pass@ep-cool-db-123456.us-east-1.aws.neon.tech/paperforge?ssl=require
```

### Vector Store & Volume Persistence Guarantee

All document chunks, vector embeddings, and database states are stored in isolated named Docker volumes (`server_chroma`, `server_data`, `server_uploads`, `postgres_data`). 
- **Embeddings Persistence**: Rebuilding images (`docker compose build --no-cache`) or restarting containers (`docker compose down && docker compose up -d`) does **NOT** wipe vector indices or uploaded PDFs.

### Multi-Stage Build & Image Size Optimization

Both `client` and `server` containers leverage multi-stage Docker builds to achieve minimal runtime footprints:
- **Client (`docker/client.Dockerfile`)**: Stage 1 uses Node 20 Alpine to compile TypeScript static bundles. Stage 2 discards Node.js, `node_modules`, and source code, shipping only static assets served by lightweight Nginx Alpine (~25MB).
- **Server (`docker/server.Dockerfile`)**: Stage 1 installs GCC, G++, and Python build dependencies to compile wheel packages. Stage 2 copies only pre-built Python binaries into a clean `python:3.11.9-slim` runtime, eliminating build tools and reducing attack surface.

### Docker Compose Profiles

PaperForge uses Docker Compose Profiles to keep development lightweight while enabling production testing:

| Environment | Command | Description | Database |
|---|---|---|---|
| **Development** | `docker compose --profile dev up -d` | React SPA + Nginx proxy, FastAPI backend, ChromaDB vector store | SQLite file |
| **Production** | `docker compose --profile prod up -d` | Multi-stage React SPA, FastAPI under Gunicorn (4 workers), ChromaDB, PostgreSQL 16 | PostgreSQL |

### Helper Scripts

Convenient helper scripts are provided under `docker/scripts/`:

- **Start Stack**: `./docker/scripts/start.sh dev` (or `.\docker\scripts\start.ps1 -Profile dev`)
- **Stop Stack**: `./docker/scripts/stop.sh` (or `.\docker\scripts\stop.ps1`)
- **Rebuild Stack**: `./docker/scripts/rebuild.sh dev` (or `.\docker\scripts\rebuild.ps1 -Profile dev`)
- **Run Migrations**: `./docker/scripts/migrate.sh dev` (or `.\docker\scripts\migrate.ps1 -Profile dev`)

### Structured Logging

Log formatting is fully configurable via `LOG_FORMAT` in `.env`:
- `LOG_FORMAT=console` (Default for dev): Human-readable colored output with correlation Request IDs.
- `LOG_FORMAT=json` (Default for prod): Single-line JSON objects tailored for Docker/Loki log aggregation.

### Troubleshooting Common Issues

1. **Port 80 / 8000 Conflict**: Ensure local web servers or standalone FastAPI instances are stopped before starting containers (`docker compose --profile dev down`).
2. **Permission Denied on Volumes**: Ensure Docker has write access to `./data`, `./uploads`, and `./chroma_data`.
3. **Database Migration Failures**: Run `.\docker\scripts\migrate.ps1 -Profile dev` to apply pending Alembic migrations inside the running backend container.

---

## Running the Test Suite

We use `pytest` for codebase verification. Run the test suite inside the `server` directory:

```bash
# Set PYTHONPATH and execute pytest
$env:PYTHONPATH="."
.venv\Scripts\pytest
```

The tests cover:
- **Chunking Service**: sliding windows, boundary checks, character limits.
- **Embedding Service**: batch processing, rate limiting, provider switching.
- **Vector Store Service**: batch insertions, NaN vector validation, dimension validations, workspace/metadata scoping filters.
- **Retrieval Service**: deduplication, parent chunk reconstruction, token limits, diagnostics.

---

## Continuous Integration & Release Engineering

PaperForge enforces automated quality gates via GitHub Actions (`.github/workflows/ci.yml` and `.github/workflows/release.yml`).

### CI Pipeline (`ci.yml`)

Every push or pull request targeting `main` or `develop` automatically executes:
1. **Backend QA**: Installs requirements, runs `pytest` test suite, generates coverage XML reports.
2. **Frontend QA**: Installs npm dependencies, runs `oxlint` (`npm run lint`), checks TypeScript types (`npm run type-check`), compiles production Vite bundle (`npm run build`).
3. **Docker QA**: Assembles `client` and `server` multi-stage Docker images, validates dev and prod Compose configs (`docker compose config`).
4. **Security Audit**: Audits Python packages (`pip-audit`) and Node dependencies (`npm audit`).
5. **CodeQL SAST Scan**: Performs static application security testing (`codeql.yml`) across Python and TypeScript.
6. **Dependabot Automated Updates**: Weekly automated dependency bump PRs (`dependabot.yml`) for `pip`, `npm`, and `github-actions`.
7. **PR Dependency Review**: Flags vulnerable package introductions prior to merging.

### Release Pipeline (`release.yml`) & Semantic Versioning

Releases follow **Semantic Versioning** (`vMAJOR.MINOR.PATCH`, e.g. `v1.0.0`):

```bash
# Tag a new release version
git tag -a v1.0.0 -m "PaperForge v1.0.0 Production Release"
git push origin v1.0.0
```

Pushing a `v*` tag triggers `.github/workflows/release.yml`, which:
1. Reuses the full CI verification suite (`ci.yml`).
2. Builds production client and server Docker images with version tags (`v1.0.0` and `latest`).
3. Publishes images to GitHub Container Registry (`ghcr.io/StarDeep18/paperforge-client` and `ghcr.io/StarDeep18/paperforge-server`).
4. Creates a GitHub Release draft with automatically generated release notes.

### Recommended GitHub Branch Protection Setup

To enforce quality gates on `main`:
1. In GitHub Repository Settings -> **Branches** -> Add Branch Protection Rule for `main`.
2. Check **Require a pull request before merging** (Minimum 1 approval).
3. Check **Require status checks to pass before merging**:
   - `Backend QA & Unit Tests`
   - `Frontend QA & Production Build`
   - `Docker Build & Compose Validation`
4. Check **Require linear history** and **Block force pushes**.

