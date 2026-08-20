# ---------------------------------------------------------------------------
# Base image: "slim" keeps the image small; pin the version for reproducibility.
# ---------------------------------------------------------------------------
FROM python:3.12-slim

# Python behaves better in containers with these:
#   - don't write .pyc files
#   - don't buffer stdout/stderr, so logs appear immediately in `docker logs`
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# ---------------------------------------------------------------------------
# Install dependencies FIRST, separately from the code.
# Docker caches this layer, so rebuilds are fast when only app code changes.
# ---------------------------------------------------------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the application code.
COPY app.py .

# ---------------------------------------------------------------------------
# Run as a non-root user. If the app is ever compromised, the blast radius
# is smaller. This is a standard production/Kubernetes expectation.
# ---------------------------------------------------------------------------
RUN useradd --create-home --uid 10001 appuser
USER appuser

# Documents the port the container listens on (informational).
EXPOSE 8000

# Optional: lets Docker mark the container healthy/unhealthy on its own.
# Orchestrators usually run their own probes, but this is handy locally.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0) if urllib.request.urlopen('http://localhost:8000/health').status==200 else sys.exit(1)"

# ---------------------------------------------------------------------------
# Production server. gunicorn runs the `app` object from app.py.
#   -w 1            : ONE worker. This app stores tasks in memory, and each
#                     gunicorn worker is a separate process with its own copy.
#                     More than one worker => a task created in worker A is
#                     invisible to worker B (inconsistent results). Once you
#                     move state to a shared store (Postgres/Redis), bump this
#                     to ~ (2 x CPU cores) + 1. This is exactly why real
#                     services keep state OUT of the process.
#   -b 0.0.0.0:8000 : bind all interfaces so the port is reachable
# ---------------------------------------------------------------------------
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:8000", "app:app"]
