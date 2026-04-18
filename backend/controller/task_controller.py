from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from schemas.task import TaskCreate, TaskRead
from utils.get_db import get_db
from repository.task_repository import TaskRepository
from service.task_service import TaskService

router = APIRouter()

# Dependency providers
async def get_task_repo(db: AsyncSession = Depends(get_db)) -> TaskRepository:
    return TaskRepository(db)

async def get_task_service(repo: TaskRepository = Depends(get_task_repo)) -> TaskService:
    return TaskService(repo)

@router.post("/", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_in: TaskCreate, 
    task_service: TaskService = Depends(get_task_service)
):
    # Placeholder for user_id - will be replaced by auth dependency later
    dummy_user_id = UUID("00000000-0000-0000-0000-000000000000")
    return await task_service.create_task(task_in, dummy_user_id)

@router.get("/", response_model=List[TaskRead])
async def read_tasks(
    skip: int = 0, 
    limit: int = 100, 
    task_service: TaskService = Depends(get_task_service)
):
    # Placeholder for user_id
    dummy_user_id = UUID("00000000-0000-0000-0000-000000000000")
    return await task_service.get_user_tasks(dummy_user_id, skip=skip, limit=limit)

@router.get("/{task_id}", response_model=TaskRead)
async def read_task(
    task_id: UUID, 
    task_service: TaskService = Depends(get_task_service)
):
    return await task_service.get_task(task_id)

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID, 
    task_service: TaskService = Depends(get_task_service)
):
    await task_service.delete_task(task_id)
    return None