from fastAPI import HTTPException, APIRouter
from models.task import Task

router = APIRouter()

@router.post("/tasks/")
async def create_task(task: Task):
    return {"message": "Task created successfully", "task": task}

@router.get("/tasks/{task_id}")
async def read_task(task_id: int):
    return {"message": "Task retrieved successfully", "task_id": task_id}

@router.put("/tasks/{task_id}")
async def update_task(task_id: int, task: Task):
    return {"message": "Task updated successfully", "task_id": task_id, "task": task}

@router.delete("/tasks/{task_id}")
async def delete_task(task_id: int):
    return {"message": "Task deleted successfully", "task_id": task_id}