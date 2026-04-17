import Base from ./Base
import uuid
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy import DateTime
from sqlalchemy import Numeric
import TaskStatus from ./enums
import TaskType from ./enums
from sqlalchemy import Enum as SqlEnum

class Task(Base):
    __table_name__ = 'task'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('user_account.id', ondelete="CASCADE" ), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(10), nullable=False)
    task_type: Mapped[TaskType] = mapped_column(SqlEnum(TaskType, native_enum = False ), nullable=False, default=TaskType.INFERENCE)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    status: Mapped[TaskStatus] = mapped_column(SqlEnum(TaskStatus, name="task_status"),String(20), nullable=False, default=TaskStatus.QUEUED)
    latency_ms: Mapped[float] = mapped_column(Numeric(precision=10,scale=2),nullable=True)
    def __repr__(self):
        return f'Task(id={self.id}, user_id={self.user_id}, name={self.name}, model={self.model}, task_type={self.task_type}, status={self.status})'
