import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.controller.user_controller import router as user_router
from backend.controller.task_controller import router as task_router
from backend.core.config import settings
from backend.service.redis_service import redis_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[api-gateway] starting...")
    yield
    print("[api-gateway] stopping...")
    await redis_service.disconnect()


def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        description="API Gateway for high-performance AI workload orchestration",
        version=settings.VERSION,
        redirect_slashes=False,
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
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
        "message": "NeuralQueue API Gateway is running",
        "version": settings.VERSION
    }