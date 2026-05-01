import asyncio
import json
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.service.redis_service import redis_service
from backend.service.ws_manager import ws_manager

async def redis_event_listener():
    print("[event-bridge] starting redis event listener...")
    pubsub = await redis_service.subscribe("task_events")
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                event = json.loads(message["data"])
                await ws_manager.broadcast(event)
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe("task_events")

@asynccontextmanager
async def lifespan(app: FastAPI):
    listener_task = asyncio.create_task(redis_event_listener())
    print("[event-bridge] standalone service running")
    yield
    print("[event-bridge] stopping...")
    listener_task.cancel()
    await asyncio.gather(listener_task, return_exceptions=True)
    await redis_service.disconnect()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # We don't expect messages from the client in this design,
            # just keeping the connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)

if __name__ == "__main__":
    uvicorn.run("backend.services.event_bridge.main:app", host="0.0.0.0", port=8001, reload=False)
