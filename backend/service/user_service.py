from datetime import timedelta
from fastapi import HTTPException, status
from typing import Optional, Tuple
from jose import jwt, JWTError

from repository.user_repository import UserRepository
from schemas.user import UserCreate, UserResponse
from core.security import verify_password, get_password_hash, create_access_token
from core.config import settings
from models.user import User

class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def register_user(self, user_in: UserCreate) -> User:
        existing_user = await self.user_repo.get_by_email(user_in.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        user_data = {
            "username": user_in.username,
            "email": user_in.email,
            "password_hash": get_password_hash(user_in.password)
        }
        return await self.user_repo.create(user_data)

    async def authenticate(self, email: str, password: str) -> Optional[User]:
        user = await self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            return None
        return user

    async def create_tokens(self, user: User) -> dict:
        access_token = create_access_token(subject=user.id)
        # Use a longer expiry for refresh tokens
        refresh_token = create_access_token(
            subject=user.id, 
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 24)
        )
        
        # Save refresh token to DB
        await self.user_repo.update(user, {"refresh_token": refresh_token})
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }

    async def refresh_token(self, refresh_token: str) -> dict:
        try:
            payload = jwt.decode(
                refresh_token, settings.SECRET_KEY, algorithms=[settings.JWT_ENCODE_ALGORITHM]
            )
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid refresh token")
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        user = await self.user_repo.get(user_id)
        if not user or user.refresh_token != refresh_token:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        return await self.create_tokens(user)
