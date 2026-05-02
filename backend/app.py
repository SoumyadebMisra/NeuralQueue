import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.controller.user_controller import router as user_router
from backend.controller.task_controller import router as task_router
from backend.core.config import settings
from backend.service.redis_service import redis_service
from backend.service.ws_manager import ws_manager

# Import the service loops
from backend.services.scheduler.main import scheduler_loop
from backend.services.worker.main import worker_loop
from backend.services.recovery.main import recovery_loop
from backend.services.event_bridge.main import redis_event_listener

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[orchestrator] starting all services in modular monolith mode...")
    
    # We run all microservices as background tasks in a single process
    tasks = [
        asyncio.create_task(redis_event_listener()),
        asyncio.create_task(scheduler_loop()),
        asyncio.create_task(recovery_loop()),
        # Run 2 workers locally in the same process
        asyncio.create_task(worker_loop("worker-1", "tasks:ready", 5)),
        asyncio.create_task(worker_loop("worker-2", "tasks:ready", 5)),
        asyncio.create_task(worker_loop("worker-3", "tasks:ready", 5)),
        asyncio.create_task(worker_loop("worker-4", "tasks:ready", 5)),
    ]
    
    yield
    
    print("[orchestrator] stopping services...")
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    await redis_service.disconnect()


def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        description="Modular Monolith Orchestrator for high-performance AI workloads",
        version=settings.VERSION,
        redirect_slashes=False,
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(user_router, prefix=f"{settings.API_V1_STR}/users", tags=["Users"])
    application.include_router(task_router, prefix=f"{settings.API_V1_STR}/tasks", tags=["Tasks"])

    return application


app = create_application()


@app.get("/", tags=["Health"])
async def health_check():
    return {
        "status": "online",
        "message": "NeuralQueue Orchestrator is running",
        "version": settings.VERSION
    }


@app.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)