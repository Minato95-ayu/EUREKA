from fastapi import WebSocket
from typing import Dict, Set
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Store active connections: {experiment_id: {websocket, ...}}
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, experiment_id: str):
        """Accept and store WebSocket connection"""
        await websocket.accept()
        
        if experiment_id not in self.active_connections:
            self.active_connections[experiment_id] = set()
        
        self.active_connections[experiment_id].add(websocket)
        logger.info(f"Client connected to experiment {experiment_id}")
    
    async def disconnect(self, websocket: WebSocket, experiment_id: str):
        """Remove WebSocket connection"""
        if experiment_id in self.active_connections:
            self.active_connections[experiment_id].discard(websocket)
            
            if not self.active_connections[experiment_id]:
                del self.active_connections[experiment_id]
        
        logger.info(f"Client disconnected from experiment {experiment_id}")
    
    async def broadcast(self, experiment_id: str, message: dict):
        """Broadcast message to all clients in experiment"""
        if experiment_id in self.active_connections:
            for connection in self.active_connections[experiment_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Broadcast error: {str(e)}")
