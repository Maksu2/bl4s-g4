"""
WebSocket manager for real-time updates.
"""

from fastapi import WebSocket
from typing import List, Dict, Any
import json
import asyncio


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket):
        """Accept and store a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
    
    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients."""
        if not self.active_connections:
            return
            
        message_text = json.dumps(message, default=str)
        
        async with self._lock:
            disconnected = []
            for connection in self.active_connections:
                try:
                    await connection.send_text(message_text)
                except Exception:
                    disconnected.append(connection)
            
            # Clean up disconnected clients
            for conn in disconnected:
                if conn in self.active_connections:
                    self.active_connections.remove(conn)
    
    async def send_job_update(self, job_id: int, status: str, progress: int, 
                               current_cycle: int = 0, message: str = None):
        """Send a job status update to all clients."""
        await self.broadcast({
            "type": "job_update",
            "job_id": job_id,
            "status": status,
            "progress": progress,
            "current_cycle": current_cycle,
            "message": message
        })
    
    async def send_system_status(self, status: str, is_running: bool, 
                                  current_job_id: int = None):
        """Send system status update to all clients."""
        await self.broadcast({
            "type": "system_status",
            "status": status,
            "is_running": is_running,
            "current_job_id": current_job_id
        })
    
    async def send_log(self, message: str, level: str = "info", job_id: int = None):
        """Send a log message to all clients."""
        from datetime import datetime
        await self.broadcast({
            "type": "log",
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "job_id": job_id
        })


# Global instance
manager = ConnectionManager()
