from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, EmailStr
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import uuid
import random
from sqlmodel import SQLModel

# --------------------
# Data Models
# --------------------

class UserCreate(BaseModel):
    user_name: Optional[str] = Field(default_factory=lambda: f"dear_guest_{str(uuid.uuid4())}"[:24])
    password: str
    email: Optional[EmailStr] = None

class UserRead(BaseModel):
    id: str
    user_name: str
    email: Optional[EmailStr] = None

class UserUpdate(BaseModel):
    user_name: str
    password: str
    email: Optional[EmailStr] = None

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
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    user_id: str
   

class ConversationRead(BaseModel):
    id: str
    user_id: str
    agent_id: str
    title: str
    total_tokens: int
    created_at: datetime



class NewConversationRequest(BaseModel):
    agent_id: str = "68a896aa-65b3-459e-a419-30aa1aa2706e"
    title: str
    user_id: str
    




# to uploaded File
class FileMeta(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str
    filename: str
    content_type: str
    upload_time: datetime = Field(default_factory=lambda: datetime.utcnow())
    size: int
