from fastapi import Depends, HTTPException, Query
from sqlmodel import Field, Session, SQLModel, create_engine, select
from sqlmodel import SQLModel
from typing import Annotated
from contextlib import contextmanager
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


async_engine = create_async_engine(DATABASE_URL, echo=True)

async_session = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

# Optional: function to create tables
async def init_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)




async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session

AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_session)]