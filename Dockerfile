# syntax=docker/dockerfile:1
FROM python:3.12-slim AS builder
WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir --prefix=/install ".[mlflow]"

FROM python:3.12-slim AS runtime
LABEL org.opencontainers.image.source="https://github.com/your-org/agentic-platform"
RUN useradd --create-home --uid 10001 appuser
WORKDIR /app
COPY --from=builder /install /usr/local
COPY src ./src
USER appuser
ENV PYTHONUNBUFFERED=1 \
    AGENTIC_ENVIRONMENT=production
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/healthz').raise_for_status()"
CMD ["uvicorn", "agentic_platform.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
