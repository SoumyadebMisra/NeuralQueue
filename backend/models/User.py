from models.Base import Base
import uuid
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

class User(Base):
    __tablename__ = 'user_account'
    id : Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(30),nullable=False)
    email: Mapped[str] = mapped_column(String(20),nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String(15),nullable=False)
    api_key: Mapped[str] = mapped_column(nullable=False, unique=True)
    def __repr__(self):
        return f'User(id={self.id}, username={self.username}, email={self.email})'