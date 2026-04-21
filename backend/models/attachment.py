from backend.models.base import Base
import uuid
from sqlalchemy import ForeignKey, String, DateTime, Enum as SqlEnum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from typing import Optional
from backend.models.enums import AttachmentType

class Attachment(Base):
    __tablename__ = 'attachment'
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('task.id', ondelete="CASCADE"), nullable=False, index=True)
    
    type: Mapped[AttachmentType] = mapped_column(SqlEnum(AttachmentType, native_enum=False), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(Text, nullable=False) # Storage URL or Link URL
    
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # For proactive reading of links
    file_size: Mapped[Optional[int]] = mapped_column(nullable=True)
    content_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    task = relationship("Task", back_populates="attachments")

    def __repr__(self):
        return f'Attachment(id={self.id}, type={self.type}, file_name={self.file_name})'

from typing import Optional
