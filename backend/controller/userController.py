from fastAPI import APIRouter, HTTPException
from models.user import User
import uuid

router = APIRouter()

@router.post("/users/")
async def create_user(user: User):
    return {"message": "User created successfully", "user": user}

@router.get("/users/{user_id}")
async def read_user(user_id: uuid.UUID):
    return {"message": "User retrieved successfully", "user_id": user_id}

@router.put("/users/{user_id}")
async def update_user(user_id: uuid.UUID, user: User):
    return {"message": "User updated successfully", "user_id": user_id, "user": user}

@router.delete("/users/{user_id}")
async def delete_user(user_id: uuid.UUID):
    return {"message": "User deleted successfully", "user_id": user_id}

@router.post("/users/login/")
async def login_user(username: str, password: str):
    return {"message": "User logged in successfully", "username": username}

@router.post("/users/logout/")
async def logout_user(username: str):
    return {"message": "User logged out successfully", "username": username}