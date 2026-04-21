from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from backend.models.task import Task
from backend.repository.base_repository import BaseRepository
from typing import List, Optional
from uuid import UUID

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
