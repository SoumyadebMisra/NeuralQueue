from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status

from repository.task_repository import TaskRepository
from schemas.task import TaskCreate
from models.task import Task
from service.redis_service import redis_service

class TaskService:
    def __init__(self, task_repo: TaskRepository):
        self.task_repo = task_repo

    async def create_task(self, task_in: TaskCreate, user_id: UUID) -> Task:
        task_data = {
            **task_in.model_dump(),
            "user_id": user_id
        }
        db_task = await self.task_repo.create(task_data)
        
        stream_name = f"tasks:{db_task.priority.value}"
        
        redis_payload = {
            "task_id": str(db_task.id),
            "task_type": str(db_task.task_type.value),
            "priority": str(db_task.priority.value),
            "gpu_budget": str(db_task.gpu_budget),
            "model": db_task.model
        }
        
        await redis_service.push_to_stream(stream_name, redis_payload)
        
        return db_task

    async def get_user_tasks(self, user_id: UUID, skip: int = 0, limit: int = 100) -> List[Task]:
        return await self.task_repo.get_by_user(user_id, skip=skip, limit=limit)

    async def get_task(self, task_id: UUID) -> Task:
        task = await self.task_repo.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task

    async def delete_task(self, task_id: UUID):
        task = await self.task_repo.delete(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task
