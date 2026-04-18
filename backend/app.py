from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from controller.user_controller import router as user_router
from controller.task_controller import router as task_router
from core.config import settings

def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        description="Backend for high-performance AI workload orchestration",
        version=settings.VERSION
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
        "message": "NeuralQueue API is running",
        "version": settings.VERSION
    }