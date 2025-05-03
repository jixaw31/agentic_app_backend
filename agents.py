from fastapi import APIRouter, HTTPException
from models import Agent, AgentConfig, AgentResponseSettings, ResponseSettings
from typing import Dict
# from contextlib import asynccontextmanager
from typing import Annotated
from fastapi import HTTPException, Query
from sqlmodel import select
from typing import Dict

from persistDB import SessionDep
from sql_models import AgentCreate

router = APIRouter()


@router.post("/", description="To create an agent with certain features.")
def create_agent(agent: Agent, session: SessionDep) -> Agent:
    agent_db = AgentCreate(
        name=agent.name,
        description=agent.description,
        welcomeMessage=agent.welcomeMessage,
        systemPrompt=agent.systemPrompt,
        tone= agent.responseSettings.tone,
        verbosity= agent.responseSettings.verbosity,
        creativity= agent.responseSettings.creativity
    )
    
    session.add(agent_db)
    session.commit()
    session.refresh(agent_db)
    return agent


@router.get("/", description="To get a list of all agents.")
def list_agents(
    session: SessionDep,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> list[AgentCreate]:
    agents = session.exec(select(AgentCreate).offset(offset).limit(limit)).all()
    return agents


@router.get("/{agent_id}", response_model=AgentCreate, description="To get a single agent by ID.")
def get_agent(agent_id: str, session: SessionDep) -> AgentCreate:
    agent = session.get(AgentCreate, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Hero not found")
    return agent


@router.put("/{agent_id}/response-settings",
             response_model=AgentCreate,
             description="""To update an agent's response settings including
                            tone, verbosity, and creativity.
                         """)
def update_response_settings(agent_id: str, settings: AgentResponseSettings, session: SessionDep):
    agent = session.get(AgentCreate, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent.tone = settings.responseSettings.tone
    agent.verbosity = settings.responseSettings.verbosity
    agent.creativity = settings.responseSettings.creativity
    session.commit()
    session.refresh(agent)
    return agent


@router.put("/{agent_id}/system-prompt", response_model=AgentCreate,
            description="To update/change the agent's system prompt.")
def update_system_prompt(agent_id: str, config: AgentConfig, session: SessionDep):
    agent = session.get(AgentCreate, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent.systemPrompt = config.systemPrompt
    session.commit()
    session.refresh(agent)
    return agent


@router.delete("/{agent_id}", description="To delete an agent.")
def delete_agent(agent_id: str, session: SessionDep):
    agent = session.get(AgentCreate, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Hero not found")
    session.delete(agent)
    session.commit()
    return {"message": f"Agent with ID: {agent_id} deleted successfully."}

