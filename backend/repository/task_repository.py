from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from backend.models.task import Task
from backend.models.enums import TaskStatus
from backend.repository.base_repository import BaseRepository
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone, timedelta

class TaskRepository(BaseRepository[Task]):
    def __init__(self, db: AsyncSession):
        super().__init__(Task, db)

    async def get(self, id: UUID) -> Optional[Task]:
        result = await self.db.execute(
            select(Task)
            .where(Task.id == id)
            .options(selectinload(Task.attachments))
        )
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: UUID, skip: int = 0, limit: int = 100) -> List[Task]:
        result = await self.db.execute(
            select(Task)
            .where(Task.user_id == user_id)
            .options(selectinload(Task.attachments))
            .offset(skip)
            .limit(limit)
            .order_by(Task.created_at.desc())
        )
        return list(result.scalars().all())

    async def try_claim_task(self, task_id: UUID, worker_name: str) -> bool:
        """
        Atomically claim a task: QUEUED → PROCESSING.
        Uses UPDATE ... WHERE status='QUEUED' — PostgreSQL's row-level lock
        guarantees only one worker can succeed. Returns True if claimed.
        """
        result = await self.db.execute(
            update(Task)
            .where(Task.id == task_id, Task.status == TaskStatus.QUEUED)
            .values(
                status=TaskStatus.PROCESSING,
                locked_by=worker_name,
                started_at=datetime.now(timezone.utc)
            )
            .returning(Task.id)
        )
        await self.db.commit()
        return result.scalar_one_or_none() is not None

    async def get_stuck_tasks(self, stuck_threshold_seconds: int = 300) -> List[Task]:
        """
        Find tasks stuck in PROCESSING for longer than the threshold.
        These are likely from crashed workers.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=stuck_threshold_seconds)
        result = await self.db.execute(
            select(Task)
            .where(
                Task.status == TaskStatus.PROCESSING,
                Task.started_at < cutoff
            )
        )
        return list(result.scalars().all())
