from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from backend.models.enums import TaskStatus, TaskType, TaskPriority
from backend.schemas.attachment import AttachmentCreate, AttachmentRead

class TaskBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    task_type: TaskType = TaskType.INFERENCE
    status: TaskStatus = TaskStatus.QUEUED
    model: str = Field(..., min_length=1, max_length=50)
    input_text: Optional[str] = None
    priority: TaskPriority = TaskPriority.LOW
    job_id: Optional[UUID] = None

class TaskCreate(TaskBase):
    attachments: List["AttachmentCreate"] = []

class TaskRead(TaskBase):
    id: UUID
    user_id: UUID
    gpu_budget: int
    retries: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    latency_ms: Optional[float] = None
    output_text: Optional[str] = None
    attachments: List["AttachmentRead"] = []

    model_config = ConfigDict(from_attributes=True)
