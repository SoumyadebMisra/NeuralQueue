from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.job import Job
from backend.models.task import Task
from backend.repository.base_repository import BaseRepository

class JobRepository(BaseRepository[Job]):
    def __init__(self, db: AsyncSession):
        super().__init__(Job, db)

    async def get(self, id: UUID) -> Optional[Job]:
        result = await self.db.execute(
            select(Job)
            .where(Job.id == id)
            .options(selectinload(Job.tasks).selectinload(Task.attachments))
        )
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: UUID, skip: int = 0, limit: int = 100) -> List[Job]:
        result = await self.db.execute(
            select(Job)
            .where(Job.user_id == user_id)
            .options(selectinload(Job.tasks).selectinload(Task.attachments))
            .offset(skip)
            .limit(limit)
            .order_by(Job.created_at.desc())
        )
        return list(result.scalars().all())
    async def delete(self, id: UUID) -> bool:
        job = await self.get(id)
        if job:
            await self.db.delete(job)
            await self.db.commit()
            return True
        return False
