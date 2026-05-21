from fastapi import WebSocket
from app.services.simulation_manager import SimulationManager
import json
import asyncio
import logging

logger = logging.getLogger(__name__)

class SimulationStreamManager:
    """Manages real-time simulation streams"""
    
    def __init__(self, sim_manager: SimulationManager):
        self.sim_manager = sim_manager
        self.active_streams = {}
    
    async def stream_simulation(
        self,
        websocket: WebSocket,
        sim_id: str,
        update_interval: float = 0.1
    ):
        """Stream simulation updates to client"""
        
        await websocket.accept()
        
        if sim_id not in self.active_streams:
            self.active_streams[sim_id] = []
        self.active_streams[sim_id].append(websocket)
        
        logger.info(f"WebSocket client connected for simulation: {sim_id}")
        
        try:
            while True:
                # Get current state from manager
                state = self.sim_manager.get_simulation_state(sim_id)
                
                # Check for errors (e.g. simulation not found)
                if "error" in state:
                    await websocket.send_json({
                        "type": "error",
                        "message": state["error"]
                    })
                    break
                
                # Send frame update to client
                await websocket.send_json({
                    "type": "simulation_update",
                    "data": state
                })
                
                # Wait before next update frame
                await asyncio.sleep(update_interval)
                
        except Exception as e:
            logger.info(f"WebSocket stream connection closed or error: {str(e)}")
        finally:
            if sim_id in self.active_streams:
                if websocket in self.active_streams[sim_id]:
                    self.active_streams[sim_id].remove(websocket)
                if not self.active_streams[sim_id]:
                    del self.active_streams[sim_id]
            try:
                await websocket.close()
            except Exception:
                pass
            logger.info(f"WebSocket client disconnected for simulation: {sim_id}")
    
    async def broadcast_simulation_update(
        self,
        sim_id: str,
        update_data: dict
    ):
        """Broadcast update to all clients watching simulation"""
        
        if sim_id in self.active_streams:
            disconnected_websockets = []
            for ws in self.active_streams[sim_id]:
                try:
                    await ws.send_json({
                        "type": "simulation_update",
                        "data": update_data
                    })
                except Exception as e:
                    logger.error(f"Broadcast error for websocket in simulation {sim_id}: {str(e)}")
                    disconnected_websockets.append(ws)
            
            for ws in disconnected_websockets:
                if ws in self.active_streams[sim_id]:
                    self.active_streams[sim_id].remove(ws)
