# PaperForge Production Cloud Deployment Guide

This guide details the production deployment architecture, cloud service configuration, secret management, CDN caching, database migration workflow, cost estimation, and monitoring for PaperForge.

---

## 1. Target Architecture Overview

```
                                    User Browser / Client
                                              │
                                              ▼
                         Cloudflare CDN & Pages (Frontend SPA)
                          https://paperforge.app (Cache Assets)
                                              │
                                       (API Proxy / CORS)
                                              ▼
                           Render Web Service (FastAPI Backend)
                                https://api.paperforge.app
                                              │
                             ┌────────────────┴────────────────┐
                             ▼                                 ▼
                 Neon Serverless PostgreSQL           Persistent Storage Mount
             [Primary Source of Truth #1]            [Primary Source of Truth #2]
             (Users, Collections, Docs, Notes)             (/app/uploads)
                                                               │
                                                               ▼
                                                      Rebuildable Vector Store
                                                         (/app/chroma_data)
```

---

## 2. Infrastructure & Hosting Component Selection

| Component | Service Provider | Purpose | Monthly Cost (Hobby) | Monthly Cost (Production) |
|---|---|---|---|---|
| **Frontend SPA** | Cloudflare Pages | React 19 SPA static hosting, CDN, SSL/TLS, Custom Domain | $0.00 | $0.00 |
| **Backend API** | Render Web Service | Multi-stage Docker container (`docker/server.Dockerfile`), Gunicorn ASGI | $7.00 | $25.00 |
| **Storage Disk** | Render Persistent Volume | Disk attached to backend (`/app/uploads` & `/app/chroma_data`) | $1.25 (5GB) | $3.00 (12GB) |
| **Database** | Neon PostgreSQL | Serverless PostgreSQL 16 (`postgresql+asyncpg://...`), PgBouncer | $0.00 | $19.00 |
| **Vector Store** | ChromaDB (In-Process) | Vector chunk embeddings & metadata index | $0.00 (Local Disk) | $0.00 (Local Disk) |
| **Total** | | | **~$8.25 / mo** | **~$47.00 / mo** |

---

## 3. Environment Variables & Secret Management

All secrets MUST be configured via Render Environment Groups and Cloudflare Environment Variables. **Never commit secrets to Git repositories.**

### Render Backend Secrets (`api.paperforge.app`)

| Variable Name | Example Value | Description |
|---|---|---|
| `APP_ENV` | `production` | Enables production mode & security policies |
| `DEBUG` | `false` | Disables debug stack trace exposure |
| `LOG_FORMAT` | `json` | Formats output to structured JSON for log aggregation |
| `SECRET_KEY` | `b9f2e7c4...` | Cryptographic secret for signing tokens |
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@ep-cool-db.us-east-1.aws.neon.tech/paperforge?ssl=require` | Managed Neon PostgreSQL URI |
| `GOOGLE_API_KEY` | `AIzaSyB...` | Google Gemini API key for LLM generation & embeddings |
| `FIREBASE_PROJECT_ID` | `paperforge-prod` | Firebase authentication project ID |
| `FIREBASE_CLIENT_EMAIL` | `firebase-adminsdk@paperforge.iam.gserviceaccount.com` | Firebase service account email |
| `FIREBASE_PRIVATE_KEY` | `"-----BEGIN PRIVATE KEY-----\nMIIEvgIBADAN...` | Firebase service account private key |
| `REQUIRE_FIREBASE_AUTH` | `true` | Enforces mandatory JWT verification on backend routes |
| `CORS_ORIGINS` | `https://paperforge.app,https://www.paperforge.app` | Allowed CORS origins for browser client |
| `SERVER_HOST` | `0.0.0.0` | Container bind address |
| `SERVER_PORT` | `8000` | Container internal port |
| `CHROMA_PERSIST_DIR` | `./chroma_data` | Path to persistent vector index directory |
| `UPLOAD_DIR` | `./uploads` | Path to persistent raw document storage directory |

---

## 4. Frontend CDN & Cache Strategy (Cloudflare Pages)

1. **Custom Domain Setup**:
   - Primary Domain: `https://paperforge.app`
   - CNAME record pointing `paperforge.app` to `<project>.pages.dev`.
   - SSL/TLS Encryption Mode: **Full (Strict)**.

2. **Cloudflare Edge Caching Rules**:
   - **Static Assets (`/assets/*.js`, `*.css`, fonts)**: Aggressive edge caching:
     `Cache-Control: public, max-age=31536000, immutable`
   - **SPA Entry (`/index.html`)**: Revalidate on every request:
     `Cache-Control: no-cache, no-store, must-revalidate`
   - **API Proxy (`/api/*`)**: Bypass CDN caching completely:
     `Cache-Control: no-store, private`

---

## 5. Backend Service Deployment (Render)

1. Connect GitHub repository to Render.
2. Select **New Web Service** -> Use Blueprint File (`deploy/render.yaml`).
3. Configure Persistent Disk:
   - **Name**: `paperforge-storage`
   - **Mount Path**: `/app/uploads` and `/app/chroma_data`
   - **Size**: 5 GB (expandable).
4. Configure Health Check Path: `/health/ready`.
5. Run Alembic Database Migrations:
   ```bash
   # Executed automatically via Render build command or shell script:
   python migrate.py upgrade head
   ```

---

## 6. Monitoring & Health Diagnostics

- **Liveness Probe**: `GET https://api.paperforge.app/health/live` — Confirms Python process responsiveness (HTTP 200).
- **Readiness Probe**: `GET https://api.paperforge.app/health/ready` — Confirms Neon DB, Firebase, and ChromaDB availability (HTTP 200 when online, HTTP 503 if degraded).
- **Uptime Monitoring**: Configure external synthetic probe (UptimeRobot / Better Stack) hitting `/health/ready` every 60 seconds with email/Slack alerting.
- **Log Aggregation**: Application streams structured single-line JSON logs to stdout, captured by Render Log Streams.
