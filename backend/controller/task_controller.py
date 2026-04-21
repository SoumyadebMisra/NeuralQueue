from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from backend.schemas.task import TaskCreate, TaskRead
from backend.schemas.job import JobCreate, JobRead
from backend.utils.get_db import get_db
from backend.repository.task_repository import TaskRepository
from backend.repository.job_repository import JobRepository
from backend.repository.attachment_repository import AttachmentRepository
from backend.service.task_service import TaskService
from backend.core.security import get_current_user
from backend.core.models_config import SUPPORTED_MODELS

router = APIRouter()

@router.get("/models")
async def get_models():
    return SUPPORTED_MODELS


async def get_task_repo(db: AsyncSession = Depends(get_db)) -> TaskRepository:
    return TaskRepository(db)

async def get_job_repo(db: AsyncSession = Depends(get_db)) -> JobRepository:
    return JobRepository(db)

async def get_attachment_repo(db: AsyncSession = Depends(get_db)) -> AttachmentRepository:
    return AttachmentRepository(db)


async def get_task_service(
    repo: TaskRepository = Depends(get_task_repo),
    job_repo: JobRepository = Depends(get_job_repo),
    att_repo: AttachmentRepository = Depends(get_attachment_repo)
) -> TaskService:
    return TaskService(repo, job_repo, att_repo)


@router.post("/", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_in: TaskCreate,
    task_service: TaskService = Depends(get_task_service),
    current_user: UUID = Depends(get_current_user)
):
    return await task_service.create_task(task_in, current_user)

@router.post("/jobs", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_in: JobCreate,
    task_service: TaskService = Depends(get_task_service),
    current_user: UUID = Depends(get_current_user)
):
    return await task_service.create_bulk_job(job_in, current_user)

@router.get("/jobs", response_model=List[JobRead])
async def read_jobs(
    skip: int = 0,
    limit: int = 100,
    task_service: TaskService = Depends(get_task_service),
    current_user: UUID = Depends(get_current_user)
):
    return await task_service.get_user_jobs(current_user, skip=skip, limit=limit)

@router.get("/jobs/{job_id}", response_model=JobRead)
async def read_job(
    job_id: UUID,
    task_service: TaskService = Depends(get_task_service),
    current_user: UUID = Depends(get_current_user)
):
    return await task_service.get_job(job_id, current_user)

@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: UUID,
    task_service: TaskService = Depends(get_task_service),
    current_user: UUID = Depends(get_current_user)
):
    await task_service.delete_job(job_id, current_user)
    return None


@router.get("/", response_model=List[TaskRead])
async def read_tasks(
    skip: int = 0,
    limit: int = 100,
    task_service: TaskService = Depends(get_task_service),
    current_user: UUID = Depends(get_current_user)
):
    return await task_service.get_user_tasks(current_user, skip=skip, limit=limit)


@router.get("/{task_id}", response_model=TaskRead)
async def read_task(
    task_id: UUID,
    task_service: TaskService = Depends(get_task_service),
    current_user: UUID = Depends(get_current_user)
):
    return await task_service.get_task(task_id, current_user)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID,
    task_service: TaskService = Depends(get_task_service),
    current_user: UUID = Depends(get_current_user)
):
    await task_service.delete_task(task_id, current_user)
    return None


@router.post("/{task_id}/retry", response_model=TaskRead)
async def retry_task(
    task_id: UUID,
    task_service: TaskService = Depends(get_task_service),
    current_user: UUID = Depends(get_current_user)
):
    return await task_service.retry_task(task_id, current_user)