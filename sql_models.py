from sqlmodel import SQLModel, Field, Relationship
from pydantic import EmailStr
import uuid
from typing import List, Optional
from datetime import datetime, timezone


class AgentCreate(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: Optional[str]
    description: Optional[str]
    welcomeMessage: Optional[str]
    systemPrompt: Optional[str]
    creativity: float = 0

# class User(SQLModel, table=True):
    
#     user_name: str
#     conversations: list["ConversationCreate"] = Relationship(back_populates="user")


class User(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_name: str = Field(index=True, max_length=24, unique=True)
    hashed_password: str
    email: Optional[str] = Field(default=None, index=True)
    
    conversations: list["ConversationCreate"] = Relationship(back_populates="user")

class ConversationCreate(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)

    user_id: str = Field(foreign_key="user.id")
    agent_id: str
    title: str
    total_tokens: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    user: Optional["User"] = Relationship(back_populates="conversations")
