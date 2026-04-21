from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.attachment import Attachment
from backend.repository.base_repository import BaseRepository

class AttachmentRepository(BaseRepository[Attachment]):
    def __init__(self, db: AsyncSession):
        super().__init__(Attachment, db)
