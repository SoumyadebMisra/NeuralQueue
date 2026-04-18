from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional
from models.enums import TaskStatus, TaskType, TaskPriority

class TaskBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    task_type: TaskType = TaskType.INFERENCE
    status: TaskStatus = TaskStatus.QUEUED
    model: str = Field(..., min_length=1, max_length=20)
    priority: TaskPriority = TaskPriority.LOW
    gpu_budget: int = Field(default=1, ge=1)

class TaskCreate(TaskBase):
    pass

class TaskRead(TaskBase):
    id: UUID
    user_id: UUID
    retries: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    latency_ms: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)
