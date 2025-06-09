from fastapi import APIRouter, HTTPException
from models import Agent, AgentUpdate, AgentRead
from typing import Dict
# from contextlib import asynccontextmanager
from typing import Annotated
from fastapi import HTTPException, Query
from sqlmodel import select
from typing import Dict
from persistDB import AsyncSessionDep
from sql_models import AgentCreate
from datetime import datetime

router = APIRouter()

example_agent = {
    "name": "medical agent",
    "description": "medical retriever agent",
    "welcomeMessage": "Hello! I’m your AI assistant for biomedical literature search.\nI have access to the following tools to help answer your questions:\n\nPubMed – for peer-reviewed scientific articles in medicine and biology.\n\nmedRxiv – for preprint research papers that have not yet undergone peer review.\n\nFeel free to ask a question, and I’ll determine the best source to search from. Let’s get started!",
    "systemPrompt": "You are an AI assistant that helps users search biomedical literature using external tools. You have access to the following tools:\\n\\nPubMed: Search peer-reviewed scientific research articles in medicine and biology.\\nUse this for formal, validated journal publications.\\n\\nmedRxiv: Search preprints in the medical field that have not yet been peer-reviewed.\\nUse this when the user wants the latest, early-stage findings or is asking for preprints.\\n\\nDo not answer directly without using a tool unless the user explicitly instructs you to.\\n\\nYou must use both tools, and retrieve three cases for each.\n\nToday is Thursday, June 05, 2025.",
    "creativity": 0.1
  }

@router.post("/", description="To create an agent with certain features.")
async def create_agent(agent: Agent, session: AsyncSessionDep):

    agent_db = AgentCreate(
        name=agent.name,
        description=agent.description,
        welcomeMessage=agent.welcomeMessage,
        systemPrompt=agent.systemPrompt,
        creativity=agent.creativity
        )
    
    session.add(agent_db)                 # ✅ not awaited
    await session.commit()               # ✅ awaited
    await session.refresh(agent_db)      # ✅ awaited
    return agent_db


@router.get("/", description="To get a list of all agents.")
async def list_agents(
    session: AsyncSessionDep,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> list[AgentRead]:
    
    results = await session.execute(select(AgentCreate).offset(offset).limit(limit))
    agents = results.scalars().all()

    
    return agents


@router.get("/{agent_id}", response_model=AgentCreate, description="To get a single agent by ID.")
async def get_agent(agent_id: str, session: AsyncSessionDep) -> AgentCreate:
    agent = session.get(AgentCreate, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Hero not found")
    return agent


@router.put("/{agent_id}",
             response_model=AgentCreate,
             description="""To update an agent's configuration like system message
                             and welcome message.
                         """)
async def update_agent(agent_id: str, agent_update: AgentUpdate, session: AsyncSessionDep):
    agent = await session.get(AgentCreate, agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # today = datetime.now().strftime("%A, %B %d, %Y")
    # system_prompt_with_date = f"{agent_update.systemPrompt}\n\nToday is {today}."

    agent.name =  agent_update.name
    agent.description =  agent_update.description
    agent.creativity =  agent_update.creativity
    agent.systemPrompt =  agent_update.systemPrompt
    agent.welcomeMessage =  agent_update.welcomeMessage

    await session.commit()
    await session.refresh(agent)
    return agent


# @router.put("/{agent_id}/system-prompt", response_model=AgentCreate,
#             description="To update/change the agent's system prompt.")
# async def update_system_prompt(agent_id: str, session: AsyncSessionDep):
#     agent = session.get(AgentCreate, agent_id)
#     if not agent:
#         raise HTTPException(status_code=404, detail="Agent not found")
    
#     agent.systemPrompt = agent.systemPrompt
#     session.commit()
#     session.refresh(agent)
#     return agent


@router.delete("/{agent_id}", description="To delete an agent.")
async def delete_agent(agent_id: str, session: AsyncSessionDep):
    agent = session.get(AgentCreate, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Hero not found")
    session.delete(agent)
    session.commit()
    return {"message": f"Agent with ID: {agent_id} deleted successfully."}


