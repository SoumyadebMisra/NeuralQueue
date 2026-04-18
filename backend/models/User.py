from models.base import Base
import uuid
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional

class User(Base):
    __tablename__ = 'user_account'
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(30), nullable=False)
    email: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, default=lambda: str(uuid.uuid4()))
    refresh_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    def __repr__(self):
        return f'User(id={self.id}, username={self.username}, email={self.email})'