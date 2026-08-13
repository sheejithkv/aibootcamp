# ═══════════════════════════════════════════════════════════════════════════════
# Dockerfile — AI Engineering Bootcamp (BlockseBlock) · Feature 12: Ship It
#
# WHAT IS A DOCKERFILE?
#   A Dockerfile is a recipe. It describes, step by step, how to build a
#   container image — a self-contained package that includes your app, its
#   dependencies, and a Python runtime. Anyone who has Docker installed can
#   run `docker compose up --build` and get an identical copy of your app,
#   regardless of their operating system or Python version.
#
# BUILD CONTEXT:
#   docker-compose.yml passes the REPO ROOT as the build context, so this
#   Dockerfile can COPY from shared/, ui/, and the solution directory.
#   Run: `docker compose up --build` from week-4-launch/feature-12-ship-it/
# ═══════════════════════════════════════════════════════════════════════════════

# ── Stage 1: dependency builder ───────────────────────────────────────────────
# We use a TWO-STAGE BUILD so the final image doesn't contain pip, gcc, or
# any of the build tools needed to compile Python packages. Smaller images
# start faster and have a smaller attack surface.
FROM python:3.12-slim AS builder

# Set the working directory for this stage.
WORKDIR /build

# Copy ONLY requirements.txt first — before any application code.
# Docker caches each instruction as a "layer." If requirements.txt hasn't
# changed, Docker reuses the cached pip install layer and skips it entirely.
# This makes rebuilds after code changes take seconds instead of minutes.
COPY requirements.txt .

# Create an isolated virtual environment so the installed packages don't
# mix with the system Python. The venv gets copied cleanly to the next stage.
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt


# ── Stage 2: runtime image ────────────────────────────────────────────────────
# Start fresh from the same slim base — no build tools, no pip cache.
# Only the virtual environment (already installed) gets copied over.
FROM python:3.12-slim AS runtime

# Copy the installed packages from the builder stage.
# This is the key multi-stage trick: we get all the packages without any
# of the installation footprint (pip, wheel, gcc, etc.)
COPY --from=builder /opt/venv /opt/venv

# Tell Python and the shell to use the venv's binaries (python, uvicorn, etc.)
ENV PATH="/opt/venv/bin:$PATH"
# Don't write .pyc bytecode files (keeps the container clean)
ENV PYTHONDONTWRITEBYTECODE=1
# Don't buffer stdout/stderr — log lines appear in `docker logs` immediately
ENV PYTHONUNBUFFERED=1

# /app is where our application code will live inside the container.
WORKDIR /app

# ── Copy application code ──────────────────────────────────────────────────────
# Copy the shared Python modules (LLM client, providers, tools, etc.)
# These live at the repo root and are needed by main.py.
COPY shared/ ./shared/

# Copy the web UI (HTML, CSS, JS — served as static files by FastAPI).
COPY ui/ ./ui/

# Copy the Feature 12 solution (the complete final application).
# This is the last COPY so that changing main.py invalidates only this
# layer — shared/ and ui/ layers stay cached.
COPY week-4-launch/feature-12-ship-it/solution/ .

# ── Data directories ──────────────────────────────────────────────────────────
# Create directories for persistent data BEFORE switching to the non-root user.
# Docker volumes will be mounted here (see docker-compose.yml).
#   /data/chroma   → Chroma vector database (document embeddings)
#   /data/uploads  → raw uploaded files (PDF, DOCX, TXT)
RUN mkdir -p /data/chroma /data/uploads

# ── Security: non-root user ───────────────────────────────────────────────────
# Running as root inside a container means if your app is exploited,
# the attacker has root access inside the container — they can read
# environment variables, write to the filesystem, and potentially escape.
#
# Creating a non-root user limits the blast radius: the attacker can run
# your app code but cannot modify system files or access other containers.
#
# This is a security best practice required by most production platforms
# (AWS App Runner, GCP Cloud Run, Azure Container Apps all enforce it).
RUN useradd --create-home appuser && chown -R appuser /app /data
USER appuser

# Document that the container listens on port 8000.
# This is informational only — docker-compose.yml handles the actual binding.
EXPOSE 8000

# Start the server.
# --host 0.0.0.0 makes the server reachable from outside the container.
# --port 8000 matches the EXPOSE above and the docker-compose ports mapping.
# --workers 1 keeps this simple; scale horizontally with multiple containers
#             rather than multiple in-process workers (easier to reason about).
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
