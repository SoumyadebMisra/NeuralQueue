from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.models.task import Task
from backend.repository.base_repository import BaseRepository
from typing import List
from uuid import UUID

class TaskRepository(BaseRepository[Task]):
    def __init__(self, db: AsyncSession):
        super().__init__(Task, db)

    async def get_by_user(self, user_id: UUID, skip: int = 0, limit: int = 100) -> List[Task]:
        result = await self.db.execute(
            select(Task)
            .where(Task.user_id == user_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
