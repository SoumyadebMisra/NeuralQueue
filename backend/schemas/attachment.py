from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional
from backend.models.enums import AttachmentType

class AttachmentBase(BaseModel):
    type: AttachmentType
    file_name: str
    file_url: str
    file_size: Optional[int] = None
    content_type: Optional[str] = None
    extracted_text: Optional[str] = None

class AttachmentCreate(AttachmentBase):
    pass

class AttachmentRead(AttachmentBase):
    id: UUID
    task_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
