from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import uuid
from sqlmodel import SQLModel

# --------------------
# Data Models
# --------------------


class Agent(BaseModel):
    name: str
    description: str
    welcomeMessage: str
    systemPrompt: str
    creativity: float

    

class AgentRead(BaseModel):
    id: str
    name: str
    description: str
    welcomeMessage: str
    systemPrompt: str
    creativity: float

    class Config:
        orm_mode = True

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    welcomeMessage: Optional[str] = None
    systemPrompt: Optional[str] = None
    creativity: Optional[float] = None
    
# --------------------
# Conversation Models
# --------------------

class Message(BaseModel):
    text: str
    

class Conversation(BaseModel):
    id: str
    agent_id: str
    title: str
    total_tokens: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        orm_mode = True

class ConversationRead(BaseModel):
    id: str
    agent_id: str
    title: str
    total_tokens: int
    created_at: datetime

    class Config:
        orm_mode = True


class NewConversationRequest(BaseModel):
    # agent_id: str
    title: str




# to uploaded File
class FileMeta(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str
    filename: str
    content_type: str
    upload_time: datetime = Field(default_factory=datetime.now(timezone.utc))
    size: int