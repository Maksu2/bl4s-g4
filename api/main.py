"""
FastAPI main application for Geant4 Simulation Dashboard.
"""

import os
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .routes import router
from .websocket import manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    init_db()
    yield
    # Shutdown (cleanup if needed)


app = FastAPI(
    title="Geant4 Simulation Dashboard API",
    description="Team-based API for managing Geant4 electromagnetic cascade simulations",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration - support environment variable for Docker/production
default_origins = [
    "http://localhost:5173",  # SvelteKit dev server
    "http://localhost:4173",  # SvelteKit preview
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:4173",
    "http://127.0.0.1:3000",
    "http://web:4173",        # Docker internal
    "https://sim.maksu.online",   # Production
    "https://api.maksu.online",   # Production API
]

# Allow additional origins from environment
env_origins = os.environ.get("CORS_ORIGINS", "")
if env_origins:
    default_origins.extend(env_origins.split(","))

app.add_middleware(
    CORSMiddleware,
    allow_origins=default_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
# Router included below with prefix


# Include API routes with /api prefix
app.include_router(router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    """Log all registered routes on startup."""
    print("=== REGISTERED ROUTES ===")
    for route in app.routes:
        if hasattr(route, "path"):
            print(f"Route: {route.path} [{','.join(route.methods)}]")
    print("=========================")


@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, receive pings
            data = await websocket.receive_text()
            # Handle client messages if needed
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await manager.disconnect(websocket)


@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "name": "Geant4 Simulation Dashboard API",
        "version": "1.0.0",
        "docs": "/docs"
    }
