# PaperForge Production Deployment Checklist

Use this pre-flight and post-flight verification checklist for every production deployment release.

---

## 1. Pre-Flight Checklist (Before Deploying)

- [ ] **CI Pipeline Green**: GitHub Actions `PaperForge CI` (`ci.yml`) passed with 0 errors across all jobs.
- [ ] **Unit Tests Passing**: 98/98 pytest backend tests passed with coverage.
- [ ] **Frontend Build Clean**: `npm run lint` and `npm run type-check` pass with 0 errors; `npm run build` generates clean `dist/` bundle.
- [ ] **Docker Containers Built**: Multi-stage Dockerfiles (`docker/client.Dockerfile` and `docker/server.Dockerfile`) build cleanly.
- [ ] **Secrets Configured**: All environment secrets (`GOOGLE_API_KEY`, `FIREBASE_*`, `DATABASE_URL`, `SECRET_KEY`) are set in platform secret managers.
- [ ] **Database Backup Verified**: Neon PostgreSQL daily snapshot or PITR point confirmed available.

---

## 2. Deployment Execution

- [ ] **Tag Version**: Git tag pushed (`git tag -a v1.0.0 -m "v1.0.0 Production Release"` & `git push origin v1.0.0`).
- [ ] **Container Push**: Production Docker images published to GHCR (`ghcr.io/StarDeep18/paperforge-client:v1.0.0` & `paperforge-server:v1.0.0`).
- [ ] **Apply Database Migrations**: Alembic migrations applied to Neon DB (`python migrate.py upgrade head`).
- [ ] **Deploy Web Service**: Render rolling deploy initiated.

---

## 3. Post-Flight Verification Checklist (Live Production)

- [ ] **HTTPS & SSL/TLS**: Access `https://paperforge.app` and verify valid SSL/TLS certificate issued by Cloudflare.
- [ ] **Liveness Probe**: `curl -f https://api.paperforge.app/health/live` returns `{"status": "live"}` (HTTP 200).
- [ ] **Readiness Probe**: `curl -f https://api.paperforge.app/health/ready` returns `{"status": "ready", "database": "connected"}` (HTTP 200).
- [ ] **Authentication**: User sign-in/sign-up succeeds via Firebase Auth.
- [ ] **Document Upload**: Upload a sample PDF paper (e.g. 5MB); verify document status transitions to `ready`.
- [ ] **RAG Search & Chat**: Send a query in Chat; verify citation-backed response with grounding snippets.
- [ ] **PDF Viewer**: Click a citation link; confirm PDF viewer opens target page and highlights matching text snippet.
- [ ] **Workspace & Collections**: Verify collections list, notes creation, and timeline event logs persist across page reloads.
- [ ] **Log Stream Health**: Inspect Render log stream; verify structured JSON logs (`LOG_FORMAT=json`) show no uncaught exceptions.
