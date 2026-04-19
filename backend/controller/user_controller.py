from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from backend.schemas.user import UserCreate, UserResponse, UserLogin, UserUpdate
from backend.utils.get_db import get_db
from backend.repository.user_repository import UserRepository
from backend.service.user_service import UserService
from backend.core.security import get_current_user
from uuid import UUID

router = APIRouter()

async def get_user_repo(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)

async def get_user_service(repo: UserRepository = Depends(get_user_repo)) -> UserService:
    return UserService(repo)

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_in: UserCreate, 
    user_service: UserService = Depends(get_user_service)
):
    return await user_service.register_user(user_in)

@router.post("/login")
async def login(
    login_data: UserLogin, 
    user_service: UserService = Depends(get_user_service)
):
    user = await user_service.authenticate(login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    result = await user_service.create_tokens(user)

    return {
        "access_token": result["access_token"],
        "token_type": "bearer"
        }

@router.post("/refresh")
async def refresh_token(
    refresh_token: str,
    user_service: UserService = Depends(get_user_service)
):
    return await user_service.refresh_token(refresh_token)

@router.get("/me", response_model=UserResponse)
async def read_user_me(
    current_user_id: UUID = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    return await user_service.get_user(current_user_id)

@router.patch("/me", response_model=UserResponse)
async def update_user_me(
    user_update: UserUpdate,
    current_user_id: UUID = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    return await user_service.update_user(current_user_id, user_update)