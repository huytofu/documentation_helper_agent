# --- Node deps (linux native chub + npm tooling under /app) ---
FROM node:20-bookworm-slim AS node_deps
WORKDIR /app
COPY package.json package-lock.json ./
# Install production deps so optional platform binaries match the image OS.
RUN npm ci --omit=dev

# --- Python agent runtime ---
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application (host node_modules excluded via .dockerignore)
COPY . .

# Linux npm tree from the Node stage (includes @nrl-ai/chub + linux binary)
COPY --from=node_deps /app/node_modules ./node_modules
COPY --from=node_deps /app/package.json ./package.json
COPY --from=node_deps /app/package-lock.json ./package-lock.json

# Prefer the native linux binary directly (no node shim required at runtime)
ENV CHUB_BIN=/app/node_modules/@nrl-ai/chub-linux-x64/chub
RUN test -x "$CHUB_BIN" || test -f "$CHUB_BIN" \
    && chmod +x "$CHUB_BIN"

ENV PORT=8080
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

CMD ["uvicorn", "agent.graph.app:app", "--host", "0.0.0.0", "--port", "8080", "--timeout-keep-alive", "300", "--proxy-headers"]
