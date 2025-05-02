from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import uuid
from sqlmodel import SQLModel

# --------------------
# Data Models
# --------------------

class AgentBase(BaseModel):
    name: str
    description: str
    welcomeMessage: str

class AgentConfig(BaseModel):
    systemPrompt: str

class ResponseSettings(BaseModel):
    tone: str
    verbosity: str
    creativity: float


class AgentResponseSettings(BaseModel):
    responseSettings: ResponseSettings

class Agent(AgentBase, AgentConfig, AgentResponseSettings):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))



# --------------------
# Conversation Models
# --------------------

class Message(BaseModel):
    sender: str  # 'user' or 'assistant'
    text: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Conversation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    messages: List[Message] = Field(default_factory=list)
    total_tokens: int = 0

class NewConversationRequest(BaseModel):
    agent_id: str

class UserMessage(BaseModel):
    text: str


# to uploaded File
class FileMeta(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str
    filename: str
    content_type: str
    upload_time: datetime = Field(default_factory=datetime.now(timezone.utc))
    size: int