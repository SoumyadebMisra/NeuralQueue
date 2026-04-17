from pydantic import BaseModel, EmailStr, Field, UUID4 as UUID, ConfigDict

class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=30)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=15)

class UserResponse(UserBase):
    id: UUID
    username: str

    model_config = ConfigDict(from_attributes=True)