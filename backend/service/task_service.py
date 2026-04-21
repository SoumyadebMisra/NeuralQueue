from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status
from backend.repository.task_repository import TaskRepository
from backend.repository.job_repository import JobRepository
from backend.repository.attachment_repository import AttachmentRepository
from backend.schemas.task import TaskCreate
from backend.schemas.job import JobCreate
from backend.models.task import Task
from backend.models.job import Job
from backend.models.attachment import Attachment
from backend.models.enums import AttachmentType
from backend.utils.scraper import scrape_url
from backend.service.redis_service import redis_service
from backend.service.resource_predictor import predict_gpu_budget

class TaskService:
    def __init__(self, task_repo: TaskRepository, job_repo: JobRepository, attachment_repo: AttachmentRepository):
        self.task_repo = task_repo
        self.job_repo = job_repo
        self.attachment_repo = attachment_repo

    async def create_task(self, task_in: TaskCreate, user_id: UUID) -> Task:
        # Predict resources based on model and prompt
        prompt = task_in.input_text or task_in.name
        predicted_gpu = predict_gpu_budget(task_in.model, prompt)
        
        # Prepare attachments (and proactive reading for links)
        attachments_to_create = []
        for att in task_in.attachments:
            if att.type == AttachmentType.LINK:
                # Proactively read the webpage
                att.extracted_text = await scrape_url(att.file_url)
            attachments_to_create.append(att.model_dump())

        task_data = {
            **task_in.model_dump(exclude={"attachments"}),
            "user_id": user_id,
            "gpu_budget": predicted_gpu
        }
        db_task = await self.task_repo.create(task_data)

        # Save attachments
        for att_data in attachments_to_create:
            att_data["task_id"] = db_task.id
            await self.attachment_repo.create(att_data)

        stream_name = f"tasks:{db_task.priority.value}"
        redis_payload = {
            "task_id": str(db_task.id),
            "task_type": str(db_task.task_type.value),
            "priority": str(db_task.priority.value),
            "gpu_budget": str(db_task.gpu_budget),
            "model": db_task.model
        }
        await redis_service.push_to_stream(stream_name, redis_payload)

        await redis_service.publish_event("task_events", {
            "type": "task_created",
            "task_id": str(db_task.id),
            "name": db_task.name,
            "priority": db_task.priority.value,
            "status": db_task.status.value,
        })

        return db_task

    async def create_bulk_job(self, job_in: JobCreate, user_id: UUID) -> Job:
        if len(job_in.tasks) > job_in.capacity_limit:
            raise HTTPException(status_code=400, detail=f"Job exceeds maximum capacity of {job_in.capacity_limit}")

        job_data = {
            "name": job_in.name,
            "user_id": user_id,
            "capacity_limit": job_in.capacity_limit
        }
        db_job = await self.job_repo.create(job_data)

        created_tasks = []
        for task_in in job_in.tasks:
            task_in.job_id = db_job.id
            task = await self.create_task(task_in, user_id)
            created_tasks.append(task)

        # Re-fetch with eager loading for capitalization/serialization
        return await self.job_repo.get(db_job.id)

    async def get_user_jobs(self, user_id: UUID, skip: int = 0, limit: int = 100) -> List[Job]:
        return await self.job_repo.get_by_user(user_id, skip=skip, limit=limit)

    async def get_job(self, job_id: UUID, user_id: UUID) -> Job:
        job = await self.job_repo.get(job_id)
        if not job or job.user_id != user_id:
            raise HTTPException(status_code=404, detail="Job not found")
        return job

    async def get_user_tasks(self, user_id: UUID, skip: int = 0, limit: int = 100) -> List[Task]:
        return await self.task_repo.get_by_user(user_id, skip=skip, limit=limit)

    async def get_task(self, task_id: UUID, user_id: UUID) -> Task:
        task = await self.task_repo.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        if task.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this task")
        return task

    async def delete_task(self, task_id: UUID, user_id: UUID):
        task = await self.task_repo.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        if task.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this task")
        
        await self.task_repo.delete(task_id)
        
        await redis_service.publish_event("task_events", {
            "type": "task_deleted",
            "task_id": str(task_id),
        })
        
        return task

    async def retry_task(self, task_id: UUID, user_id: UUID) -> Task:
        task = await self.task_repo.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        if task.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to retry this task")
        
        # Reset task state
        from backend.models.enums import TaskStatus
        task.status = TaskStatus.QUEUED
        task.retries = 0
        task.output_text = None
        task.started_at = None
        task.completed_at = None
        task.latency_ms = None
        
        await self.task_repo.update(task, {
            "status": task.status,
            "retries": task.retries,
            "output_text": task.output_text,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "latency_ms": task.latency_ms
        })

        # Re-enqueue
        stream_name = f"tasks:{task.priority.value}"
        redis_payload = {
            "task_id": str(task.id),
            "task_type": str(task.task_type.value),
            "priority": str(task.priority.value),
            "gpu_budget": str(task.gpu_budget),
            "model": task.model
        }
        await redis_service.push_to_stream(stream_name, redis_payload)

        await redis_service.publish_event("task_events", {
            "type": "task_retried",
            "task_id": str(task_id),
            "status": task.status.value,
        })
        
        return task

    async def delete_job(self, job_id: UUID, user_id: UUID):
        job = await self.job_repo.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        if job.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this job")
        
        await self.job_repo.delete(job_id)
        
        await redis_service.publish_event("task_events", {
            "type": "job_deleted",
            "job_id": str(job_id),
        })
        
        return job
