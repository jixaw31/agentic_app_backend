from fastapi import APIRouter, HTTPException, Depends, Query
from models import *
from typing import Dict, List
from dotenv import load_dotenv
from langchain_deepseek import ChatDeepSeek
from langchain_core.prompts import ChatPromptTemplate
import os
from typing import Annotated
from sqlmodel import select
from sql_models import AgentCreate, ConversationCreate
from persistDB import SessionDep
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, ToolMessage, AIMessage
from graph import stream_graph_updates, graph

load_dotenv() 

router = APIRouter()

# in memory db
conversations_db: Dict[str, Conversation] = {}

# LLM logic
os.environ["DEEPSEEK_API_KEY"] = os.getenv("DEEPSEEK_API_KEY")

llm = ChatDeepSeek(
    model="deepseek-chat",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)

def generate_response_calc_token(input_:str, agent: Agent, history: List[Message]):
    prompt = ChatPromptTemplate.from_messages(
    [
        ("system", agent.systemPrompt),
        ("human", "{input}"),
    ]
    )
    chain = prompt | llm
    res = chain.invoke(
        {"input": input_}
    )
    return res.content,\
           res.response_metadata['token_usage']['completion_tokens'],\
           res.response_metadata['token_usage']['prompt_tokens']



@router.post("/", response_model=Conversation)
def start_conversation(request: NewConversationRequest, session: SessionDep):
    agent = session.get(AgentCreate, request.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Hero not found")
    
    convo = ConversationCreate(agent_id=request.agent_id,
                               total_tokens=0)
    
    conv_config = {"configurable": {"thread_id": convo.id}}

    system_message = [SystemMessage(content = agent.systemPrompt)]
    graph.update_state(
        conv_config,
        {"messages": system_message},
    )

    # updating graph with AI welcome message
    welcome_message = [AIMessage(content = agent.welcomeMessage)]

    graph.update_state(
        conv_config,
        {"messages": welcome_message},
    )
    session.add(convo)
    session.commit()
    session.refresh(convo)
    return convo


@router.post("/{conversation_id}/message")
def send_message(conversation_id: str, message:Message, session: SessionDep):
    
    convo = session.get(ConversationCreate, conversation_id)
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    agent = session.get(AgentCreate, convo.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    conv_config = {"configurable": {"thread_id": convo.id}}
    res_content, completion_tokens, prompt_tokens = stream_graph_updates(message.text,
                                                                         conv_config)

    convo.total_tokens += prompt_tokens
    convo.total_tokens += completion_tokens

    return {"user": (message.text, prompt_tokens), "assistant": (res_content, completion_tokens)}


@router.get("/", response_model=List[ConversationCreate])
def get_all_conversations(session: SessionDep,
                          offset: int = 0,
                          limit: Annotated[int, Query(le=100)] = 100
                          ):
    conversations = session.exec(select(ConversationCreate).offset(offset).limit(limit)).all()
    return conversations

@router.get("/{conversation_id}", response_model=Conversation)
def get_conversation(conversation_id: str, session: SessionDep):
    conversation = session.get(ConversationCreate, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


# @router.get("/agent/{agent_id}", response_model=List[Conversation])
# def list_agent_conversations(agent_id: str):
#     if agent_id not in agents_db:
#         raise HTTPException(status_code=404, detail="Agent not found")
#     return [c for c in conversations_db.values() if c.agent_id == agent_id]
