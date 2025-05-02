from sqlmodel import SQLModel, Field, Relationship
import uuid
from typing import List

class AgentCreate(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    description: str
    welcomeMessage: str
    systemPrompt: str
    tone: str
    verbosity: str
    creativity: float


class ConversationCreate(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    agent_id: str
    total_tokens: int = 0
    # session_id: str

