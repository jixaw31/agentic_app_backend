from fastapi import APIRouter, HTTPException
from models import Agent, AgentUpdate, AgentRead, UserCreate, UserRead, UserUpdate
from typing import Dict, List
# from contextlib import asynccontextmanager
from typing import Annotated
from fastapi import HTTPException, Query
from sqlmodel import select
from typing import Dict
from persistDB import AsyncSessionDep
from sql_models import AgentCreate, User
from datetime import datetime
import bcrypt
from fastapi import HTTPException, status
from passlib.context import CryptContext
from utils.jwt_handler import create_access_token

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

@router.post("/create-user", response_model=UserRead, description="To create a user.")
async def create_user(user: UserCreate, session: AsyncSessionDep):
    if not user.password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password is required")

    hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    user_db = User(
        user_name=user.user_name,
        hashed_password=hashed_password,
        email=user.email
    )

    session.add(user_db)
    await session.commit()
    await session.refresh(user_db)

    return user_db


@router.post("/sign-in")
async def sign_in(user: UserCreate, session: AsyncSessionDep):
    if not user.user_name or not user.password:
        raise HTTPException(status_code=400, detail="Username and password are required")

    result = await session.execute(select(User).where(User.user_name == user.user_name))
    db_user = result.scalar_one_or_none()

    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": db_user.user_name})
    return {
        "access_token": token,
        "token_type": "bearer",
        "id": db_user.id,
        "user_name": db_user.user_name,
    }

@router.get("/", response_model=List[UserRead], description="To get a list of all users.")
async def list_users(
    session: AsyncSessionDep,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
):
    results = await session.execute(select(User).offset(offset).limit(limit))
    users = results.scalars().all()
    return users


@router.get("/users/{user_id}", response_model=UserRead, description="To get a single user by ID.")
async def get_user(user_id: str, session: AsyncSessionDep) -> UserRead:
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/update-user/{user_id}", response_model=UserRead, description="To update a user's data.")
async def update_user(user_id: str, user_update: UserUpdate, session: AsyncSessionDep):
    user = await session.get(User, user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user_update.user_name is not None:
        user.user_name = user_update.user_name

    if user_update.password is not None:
        user.hashed_password = hash_password(user_update.password)

    if user_update.email is not None:
        user.email = user_update.email

    await session.commit()
    await session.refresh(user)
    return user


@router.delete("/{user_id}", description="To delete a user.")
async def delete_user(user_id: str, session: AsyncSessionDep):
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await session.delete(user)
    await session.commit()
    return {"message": f"User with ID: {user_id} deleted successfully."}