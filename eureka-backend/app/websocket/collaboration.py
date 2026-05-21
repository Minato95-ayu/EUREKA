from fastapi import WebSocket
from typing import Dict, Set
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

class CollaborationManager:
    """Manages real-time collaboration"""
    
    def __init__(self):
        self.active_collaborations: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, collab_id: str):
        """Connect to collaboration"""
        await websocket.accept()
        
        if collab_id not in self.active_collaborations:
            self.active_collaborations[collab_id] = set()
        
        self.active_collaborations[collab_id].add(websocket)
        logger.info(f"User connected to collaboration: {collab_id}")
    
    async def disconnect(self, websocket: WebSocket, collab_id: str):
        """Disconnect from collaboration"""
        if collab_id in self.active_collaborations:
            self.active_collaborations[collab_id].discard(websocket)
            if not self.active_collaborations[collab_id]:
                del self.active_collaborations[collab_id]
        
        logger.info(f"User disconnected from collaboration: {collab_id}")
    
    async def broadcast_change(
        self,
        collab_id: str,
        change_data: Dict,
        sender_id: str = None
    ):
        """Broadcast change to all collaborators"""
        if collab_id not in self.active_collaborations:
            return
        
        message = {
            "type": "change",
            "data": change_data,
            "sender_id": sender_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Make a copy to avoid modification during iteration
        for connection in list(self.active_collaborations[collab_id]):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Broadcast error: {str(e)}")
                self.active_collaborations[collab_id].discard(connection)
    
    async def broadcast_comment(
        self,
        collab_id: str,
        comment: Dict
    ):
        """Broadcast new comment"""
        if collab_id not in self.active_collaborations:
            return
        
        message = {
            "type": "comment",
            "data": comment,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        for connection in list(self.active_collaborations[collab_id]):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Broadcast error: {str(e)}")
                self.active_collaborations[collab_id].discard(connection)
