from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional
from models.enums import TaskStatus, TaskType

class TaskBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    task_type: TaskType = TaskType.GENERAL
    status: TaskStatus = TaskStatus.PENDING
    model: str = Field(..., min_length=1, max_length=10)

class TaskCreate(TaskBase):
    pass

class TaskRead(TaskBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    latency_ms: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)
