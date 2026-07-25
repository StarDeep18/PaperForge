# PaperForge Emergency Rollback Procedure

This document outlines the step-by-step procedure for rolling back application containers, managing database migration rollbacks safely, and restoring service after a failed deployment.

---

## 1. Operational Rollback Decision Tree

```
                       Production Deployment Incident Detected
                                          │
                                          ▼
                      Is the failure caused by application code?
                                     /         \
                                    YES         NO
                                    /             \
                       Revert Container Image      Database Schema / Data Issue?
                                 │                            │
                                 ▼                            ▼
                       Verify /health/ready         Is migration safely reversible?
                                                              /              \
                                                             YES              NO
                                                             /                  \
                                                   alembic downgrade -1     Restore Neon PITR Backup
```

---

## 2. Step 1: Application Container Rollback (Primary Procedure)

Rolling back the application container is the safest and fastest way to restore service when a deployment fails due to backend application code or frontend assets.

### Procedure (Render Dashboard)

1. Log into **Render Dashboard** -> Navigate to `paperforge-server` Web Service.
2. Go to **Deploys** tab.
3. Locate the previous **Successful Deployment** tag (e.g., `ghcr.io/StarDeep18/paperforge-server:v1.0.0`).
4. Click **Roll Back to This Deploy**.
5. Render will perform a zero-downtime rolling restart to the previous container image.

### Procedure (CLI)

```bash
# Roll back to specific image tag via Render API or Docker Compose
docker pull ghcr.io/StarDeep18/paperforge-server:v1.0.0
```

---

## 3. Step 2: Safe Database Migration Rollback Policy

> [!CAUTION]
> **NEVER** run `alembic downgrade -1` blindly in production! Forced database downgrades on destructive schema changes (column drops, type alterations, data transformations) can result in irreversible data loss.

### Safe Downgrade Criteria

`alembic downgrade -1` is permitted **ONLY** if:
1. The migration script contains an explicit, non-destructive `downgrade()` implementation.
2. The schema change only added nullable columns or non-critical indexes.
3. The downgrade has been verified in staging without data loss.

### Database Downgrade Execution

If the migration meets the safe downgrade criteria:
```bash
# Execute downgrade inside running server shell or Render SSH session:
python migrate.py downgrade -1
```

### Complex / Destructive Schema Rollback (Point-in-Time Recovery)

If the failed migration altered existing data or dropped tables:
1. **DO NOT** run `alembic downgrade`.
2. Open **Neon Console** -> Navigate to **Backups / Branching**.
3. Select **Point-in-Time Recovery (PITR)**.
4. Pick the precise timestamp prior to the deployment execution (e.g., `2026-07-25 21:00:00 UTC`).
5. Restore database state to a new production branch or overwrite main DB branch.
6. Restart `paperforge-server` container to point to the restored DB endpoint.

---

## 4. Post-Rollback Verification Checklist

- [ ] Liveness probe returns 200 OK: `curl https://api.paperforge.app/health/live`
- [ ] Readiness probe returns 200 OK: `curl https://api.paperforge.app/health/ready`
- [ ] Log stream shows no repeating error traces (`LOG_FORMAT=json`).
- [ ] Frontend SPA loads cleanly at `https://paperforge.app`.
- [ ] User authentication and JWT verification operate normally.
- [ ] Document list, PDF viewer, RAG chat, notes, and timeline function correctly.
