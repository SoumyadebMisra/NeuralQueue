from pydantic import BaseModel, EmailStr, Field, UUID4 as UUID, ConfigDict
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=30)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=15)

class UserUpdate(BaseModel):
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None

class UserResponse(UserBase):
    id: UUID
    username: str
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class UserLogin(BaseModel):
    email: EmailStr
    password: str