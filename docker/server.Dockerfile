# Stage 1: Build dependencies & Python wheels
FROM python:3.11.9-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY server/requirements.txt ./
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Minimal runtime image
FROM python:3.11.9-slim AS runner

LABEL org.opencontainers.image.title="PaperForge Server"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.authors="PaperForge Team"
LABEL org.opencontainers.image.description="FastAPI Backend Application for PaperForge"

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/install/bin:$PATH" \
    PYTHONPATH="/install/lib/python3.11/site-packages:$PYTHONPATH"

# Install curl/runtime requirements if needed for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /install
COPY server/ ./

EXPOSE 8000

STOPSIGNAL SIGTERM

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "--graceful-timeout", "30", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-"]
