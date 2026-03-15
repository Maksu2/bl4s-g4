# Geant4 Simulation Dashboard - Home Assistant Add-on
# Unified multi-service container for aarch64 (Raspberry Pi 5)

# ============ Build Stage: Frontend ============
FROM node:20-alpine AS web-builder

WORKDIR /app/web

COPY web/package*.json ./
RUN npm ci

COPY web/ ./
RUN npm run build

# ============ Production Stage ============
FROM ghcr.io/home-assistant/aarch64-base-debian:bookworm

# Add-on labels
LABEL \
    io.hass.name="Geant4 Simulation Dashboard" \
    io.hass.description="Team simulation dashboard with Cloudflare Tunnel" \
    io.hass.arch="aarch64" \
    io.hass.type="addon" \
    io.hass.version="1.0.0"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    nodejs \
    npm \
    curl \
    jq \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Install cloudflared for aarch64
RUN curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64 \
    -o /usr/local/bin/cloudflared \
    && chmod +x /usr/local/bin/cloudflared

# Create application directories
WORKDIR /app

# ==================== API Setup ====================
COPY api/requirements.txt ./api/requirements.txt

# Create virtual environment and install Python dependencies
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r api/requirements.txt

COPY api/ ./api/
COPY visualize_results.py ./

# ==================== Web Setup ====================
COPY --from=web-builder /app/web/build ./web/build
COPY --from=web-builder /app/web/package.json ./web/

# Install production Node.js dependencies
WORKDIR /app/web
RUN npm install --omit=dev
WORKDIR /app

# ==================== Geant4 Binary ====================
# Copy pre-built GeantSim binary (must be compiled for aarch64)
# The binary should be placed in addon/bin/GeantSim before building
COPY bin/GeantSim ./build/GeantSim
RUN chmod +x ./build/GeantSim || true

# Create data directory for results
RUN mkdir -p /data/results /data/db

# ==================== Run Script ====================
COPY run.sh /
RUN chmod +x /run.sh

# Expose ports (internal, tunnel handles external)
EXPOSE 8000 4173

# Run the supervisor script
CMD ["/run.sh"]
