from sqlmodel import SQLModel, Field, Relationship
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


class ConversationCreate(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    agent_id: str
    title: str
    total_tokens: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)

