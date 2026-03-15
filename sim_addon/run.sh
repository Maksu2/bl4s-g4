#!/usr/bin/env bashio
# Geant4 Simulation Dashboard - Supervisor

set -e

# Read tunnel token from config
# Read tunnel token from config
# TUNNEL_TOKEN=$(bashio::config 'tunnel_token')
TUNNEL_TOKEN="eyJhIjoiNDNhZWRlYTI1NGU0NzM4YjBiOWJhNTVjZjQ4MWRmMjAiLCJ0IjoiMzk3M2I0MDQtMzEwNi00MzRlLTg1YTMtYWZjYTI3MmQ5OWRlIiwicyI6IlpqVmtORFl6TnpjdE1qazRNQzAwTUdNNUxUZzJNbVF0WlRsbVpERTNOV1ZqT1dVdyJ9"

bashio::log.info "=== Geant4 Simulation Dashboard ==="

# Environment
export PYTHONUNBUFFERED=1
export PATH="/opt/venv/bin:$PATH"
export HOST="0.0.0.0"
export PORT=4173
export ORIGIN="https://sim.maksu.online"
export RESULTS_DIR="/data/results"
export PROJECT_ROOT="/app"

mkdir -p /data/results /data/db

# PID tracking
API_PID="" WEB_PID="" TUNNEL_PID=""

cleanup() {
    bashio::log.info "Shutting down..."
    [ -n "$TUNNEL_PID" ] && kill "$TUNNEL_PID" 2>/dev/null || true
    [ -n "$WEB_PID" ] && kill "$WEB_PID" 2>/dev/null || true
    [ -n "$API_PID" ] && kill "$API_PID" 2>/dev/null || true
    exit 0
}
trap cleanup SIGTERM SIGINT

# Start API
bashio::log.info "Starting API on :8000..."
cd /app && python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!
sleep 3

# Start Web
bashio::log.info "Starting Web on :4173..."
cd /app/web && node build &
WEB_PID=$!
sleep 2

# Start Tunnel
if [ -n "$TUNNEL_TOKEN" ]; then
    bashio::log.info "Starting Cloudflare Tunnel..."
    cloudflared tunnel run --token "$TUNNEL_TOKEN" &
    TUNNEL_PID=$!
    bashio::log.info "✓ Tunnel active"
else
    bashio::log.warning "Brak tunnel_token - dostęp tylko lokalny"
fi

bashio::log.info "=== Wszystko działa! ==="

# Keep alive
while true; do
    kill -0 "$API_PID" 2>/dev/null || { bashio::log.error "API died"; cd /app && python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 & API_PID=$!; }
    kill -0 "$WEB_PID" 2>/dev/null || { bashio::log.error "Web died"; cd /app/web && node build & WEB_PID=$!; }
    [ -n "$TUNNEL_TOKEN" ] && [ -n "$TUNNEL_PID" ] && ! kill -0 "$TUNNEL_PID" 2>/dev/null && { cloudflared tunnel run --token "$TUNNEL_TOKEN" & TUNNEL_PID=$!; }
    sleep 10
done
