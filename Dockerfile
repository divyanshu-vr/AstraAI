# syntax=docker/dockerfile:1
# Astra on Hugging Face Spaces (Docker SDK, CPU). Multi-stage: build the React
# frontend, then a slim Python image that bakes the demo workspace at build time.
# NOTE: HF Spaces run the container as UID 1000, so we create that user and own
# everything it writes (Chroma opens its SQLite read-write — must be user-owned).

# ---------- stage 1: frontend ----------
FROM node:20-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---------- stage 2: app ----------
FROM python:3.11-slim

# git: needed at build (clone) and runtime (gitstats / live add-repo). apt needs root.
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# Create + switch to UID 1000 BEFORE any pip/copy/bake so all files are user-owned.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    EMBED_PROVIDER=fastembed \
    EMBED_GPU=0 \
    ASTRA_HOST=0.0.0.0 \
    ASTRA_PORT=7860 \
    ASTRA_SEED=1 \
    HF_HOME=/home/user/app/.cache/hf \
    FASTEMBED_CACHE_PATH=/home/user/app/.cache/fastembed
WORKDIR /home/user/app

COPY --chown=user requirements-hf.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements-hf.txt

COPY --chown=user astra/ ./astra/
COPY --chown=user deploy/ ./deploy/
COPY --chown=user --from=web /web/dist ./frontend/dist

# NOTE: we do NOT embed at build — HF's free build VM OOMs on onnxruntime. Instead the
# server seeds the demo workspace at RUNTIME (ASTRA_SEED=1, 16GB) in a background thread;
# repo cards fill in live (~3 min on first boot). Keeps the build light and OOM-proof.
EXPOSE 7860
CMD ["python", "-m", "astra.server"]
