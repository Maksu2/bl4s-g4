# Geant4 Simulation Dashboard
# Home Assistant Add-on for aarch64 (Raspberry Pi 5)

# ============ Build Stage: Frontend ============
FROM node:20-alpine AS web-builder

WORKDIR /app/web
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# ============ Production Stage ============
FROM ghcr.io/home-assistant/aarch64-base-debian:bookworm

LABEL io.hass.name="Geant4 Simulation Dashboard" \
    io.hass.description="Panel symulacji Geant4" \
    io.hass.arch="aarch64" \
    io.hass.type="addon" \
    io.hass.version="1.0.0"

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    nodejs npm curl jq procps \
    && rm -rf /var/lib/apt/lists/*

# Install cloudflared
RUN curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64 \
    -o /usr/local/bin/cloudflared && chmod +x /usr/local/bin/cloudflared

WORKDIR /app

# Python dependencies
COPY api/requirements.txt ./api/requirements.txt
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r api/requirements.txt

# Copy application code
COPY api/ ./api/
COPY visualize_results.py ./
COPY build/GeantSim ./build/GeantSim
RUN chmod +x ./build/GeantSim || true

# Copy frontend build
COPY --from=web-builder /app/web/build ./web/build
COPY --from=web-builder /app/web/package.json ./web/
WORKDIR /app/web
RUN npm install --omit=dev
WORKDIR /app

# Create data directories
RUN mkdir -p /data/results /data/db

# Copy run script
COPY run.sh /run.sh
RUN chmod +x /run.sh

EXPOSE 8000 4173
CMD ["/run.sh"]
