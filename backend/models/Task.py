from backend.models.base import Base
import uuid
from sqlalchemy import ForeignKey, String, DateTime, Numeric, Enum as SqlEnum, Text
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from typing import Optional
from backend.models.enums import TaskStatus, TaskType, TaskPriority
from sqlalchemy import Integer

class Task(Base):
    __tablename__ = 'task'
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('user_account.id', ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(50), nullable=False)
    input_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    task_type: Mapped[TaskType] = mapped_column(SqlEnum(TaskType, native_enum=False), nullable=False, default=TaskType.INFERENCE)
    
    priority: Mapped[TaskPriority] = mapped_column(SqlEnum(TaskPriority, native_enum=False), nullable=False, default=TaskPriority.LOW)
    gpu_budget: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    
    status: Mapped[TaskStatus] = mapped_column(SqlEnum(TaskStatus, native_enum=False), nullable=False, default=TaskStatus.QUEUED)
    latency_ms: Mapped[float] = mapped_column(Numeric(precision=10, scale=2), nullable=True)
    retries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f'Task(id={self.id}, name={self.name}, status={self.status}, priority={self.priority})'
