from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional
from backend.models.enums import TaskStatus, TaskType, TaskPriority

class TaskBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    task_type: TaskType = TaskType.INFERENCE
    status: TaskStatus = TaskStatus.QUEUED
    model: str = Field(..., min_length=1, max_length=50)
    input_text: Optional[str] = None
    priority: TaskPriority = TaskPriority.LOW

class TaskCreate(TaskBase):
    pass

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

    model_config = ConfigDict(from_attributes=True)
