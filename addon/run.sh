#!/usr/bin/env bashio
#
# Geant4 Simulation Dashboard - Add-on Run Script
# Manages all services: API, Web, Cloudflare Tunnel
#

set -e

# =================================================================
# Configuration
# =================================================================
CONFIG_PATH="/data/options.json"

# Read configuration from Home Assistant
TUNNEL_TOKEN=$(bashio::config 'tunnel_token')
DOMAIN_WEB=$(bashio::config 'domain_web' 'sim.maksu.online')
DOMAIN_API=$(bashio::config 'domain_api' 'api.maksu.online')
LOG_LEVEL=$(bashio::config 'log_level' 'info')

bashio::log.info "=== Geant4 Simulation Dashboard ==="
bashio::log.info "Web Domain: ${DOMAIN_WEB}"
bashio::log.info "API Domain: ${DOMAIN_API}"
bashio::log.info "Log Level: ${LOG_LEVEL}"

# =================================================================
# Environment Setup
# =================================================================
export PYTHONUNBUFFERED=1
export PATH="/opt/venv/bin:$PATH"

# Set API URL for frontend
export PUBLIC_API_URL="https://${DOMAIN_API}"
export ORIGIN="https://${DOMAIN_WEB}"
export HOST="0.0.0.0"
export PORT=4173

# Database path (persistent storage)
export DATABASE_URL="sqlite:////data/db/simulations.db"

# Results directory (shared storage)
export RESULTS_DIR="/data/results"
mkdir -p "${RESULTS_DIR}"

# =================================================================
# PID tracking for graceful shutdown
# =================================================================
API_PID=""
WEB_PID=""
TUNNEL_PID=""

cleanup() {
    bashio::log.info "Shutting down services..."
    
    if [[ -n "${TUNNEL_PID}" ]]; then
        kill "${TUNNEL_PID}" 2>/dev/null || true
    fi
    if [[ -n "${WEB_PID}" ]]; then
        kill "${WEB_PID}" 2>/dev/null || true
    fi
    if [[ -n "${API_PID}" ]]; then
        kill "${API_PID}" 2>/dev/null || true
    fi
    
    wait
    bashio::log.info "All services stopped."
    exit 0
}

trap cleanup SIGTERM SIGINT

# =================================================================
# Start Services
# =================================================================

# --- Start FastAPI Backend ---
bashio::log.info "Starting FastAPI backend on port 8000..."
cd /app
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --log-level "${LOG_LEVEL}" &
API_PID=$!

# Wait for API to be ready
bashio::log.info "Waiting for API to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        bashio::log.info "✓ API is ready"
        break
    fi
    sleep 1
done

# --- Start SvelteKit Frontend ---
bashio::log.info "Starting SvelteKit frontend on port 4173..."
cd /app/web
node build &
WEB_PID=$!

# Wait for frontend to be ready
bashio::log.info "Waiting for frontend to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:4173/ > /dev/null 2>&1; then
        bashio::log.info "✓ Frontend is ready"
        break
    fi
    sleep 1
done

# --- Start Cloudflare Tunnel ---
if [[ -n "${TUNNEL_TOKEN}" ]]; then
    bashio::log.info "Starting Cloudflare Tunnel..."
    cloudflared tunnel run --token "${TUNNEL_TOKEN}" &
    TUNNEL_PID=$!
    bashio::log.info "✓ Cloudflare Tunnel started"
    bashio::log.info "Access your dashboard at: https://${DOMAIN_WEB}"
else
    bashio::log.warning "No tunnel token configured - external access disabled"
    bashio::log.info "Configure tunnel_token in add-on settings for external access"
fi

# =================================================================
# Keep running and monitor processes
# =================================================================
bashio::log.info "=== All services running ==="

while true; do
    # Check if API is still running
    if ! kill -0 "${API_PID}" 2>/dev/null; then
        bashio::log.error "API process died, restarting..."
        cd /app
        python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --log-level "${LOG_LEVEL}" &
        API_PID=$!
    fi
    
    # Check if Web is still running
    if ! kill -0 "${WEB_PID}" 2>/dev/null; then
        bashio::log.error "Web process died, restarting..."
        cd /app/web
        node build &
        WEB_PID=$!
    fi
    
    # Check tunnel if configured
    if [[ -n "${TUNNEL_TOKEN}" ]] && [[ -n "${TUNNEL_PID}" ]]; then
        if ! kill -0 "${TUNNEL_PID}" 2>/dev/null; then
            bashio::log.error "Tunnel process died, restarting..."
            cloudflared tunnel run --token "${TUNNEL_TOKEN}" &
            TUNNEL_PID=$!
        fi
    fi
    
    sleep 10
done
