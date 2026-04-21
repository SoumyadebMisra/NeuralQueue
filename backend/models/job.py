from backend.models.base import Base
import uuid
from sqlalchemy import ForeignKey, String, DateTime, Enum as SqlEnum, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from backend.models.enums import TaskStatus

class Job(Base):
    __tablename__ = 'job'
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('user_account.id', ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(SqlEnum(TaskStatus, native_enum=False), nullable=False, default=TaskStatus.QUEUED)
    capacity_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    tasks = relationship("Task", back_populates="job", cascade="all, delete-orphan")

    def __repr__(self):
        return f'Job(id={self.id}, name={self.name}, status={self.status})'
