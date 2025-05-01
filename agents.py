from fastapi import APIRouter, HTTPException
from models import Agent, AgentConfig, AgentResponseSettings
from typing import Dict, List

router = APIRouter()

# in memory DB
agents_db: Dict[str, Agent] = {}

@router.post("/", response_model=Agent)
def create_agent(agent: Agent):
    if agent.id in agents_db:
        raise HTTPException(status_code=400, detail="Agent already exists.")
    agents_db[agent.id] = agent
    return agent

@router.get("/", response_model=List[Agent])
def list_agents():
    return list(agents_db.values())

@router.get("/{agent_id}", response_model=Agent)
def get_agent(agent_id: str):
    agent = agents_db.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@router.put("/{agent_id}/system-prompt", response_model=Agent)
def update_system_prompt(agent_id: str, config: AgentConfig):
    agent = agents_db.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent.systemPrompt = config.systemPrompt
    return agent

@router.put("/{agent_id}/response-settings", response_model=Agent)
def update_response_settings(agent_id: str, settings: AgentResponseSettings):
    agent = agents_db.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent.responseSettings = settings.responseSettings
    return agent

@router.delete("/{agent_id}")
def delete_agent(agent_id: str):
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    del agents_db[agent_id]
    return {"message": f"Agent {agent_id} deleted successfully."}
