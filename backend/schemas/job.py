from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import List, Optional
from backend.models.enums import TaskStatus
from backend.schemas.task import TaskRead, TaskCreate

class JobBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    status: TaskStatus = TaskStatus.QUEUED
    capacity_limit: int = 20

class JobCreate(JobBase):
    tasks: List[TaskCreate]

class JobRead(JobBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    tasks: List[TaskRead] = []

    model_config = ConfigDict(from_attributes=True)
