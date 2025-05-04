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
from graph import stream_graph_updates, create_graph

load_dotenv() 

router = APIRouter()

graphs = dict()

@router.post("/", response_model=Conversation,
              description="""To create a conversation,
                by employing a certain agent.(grabbing agent by ID)""")
def start_conversation(request: NewConversationRequest, session: SessionDep):
    agent = session.get(AgentCreate, request.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Hero not found")
    
    convo = ConversationCreate(agent_id=request.agent_id,
                               total_tokens=0)
    

    conv_config = {"configurable": {"thread_id": convo.id}}
    graph = create_graph(f'{agent.name}_db', agent.creativity)

    graphs['1'] = graph

    # graphs[convo.id] = graph


    system_message = [SystemMessage(content = agent.systemPrompt)]
    graph.update_state(
        conv_config,
        {"messages": system_message},
    )

    welcome_message = [AIMessage(content = agent.welcomeMessage)]
    graph.update_state(
        conv_config,
        {"messages": welcome_message},
    )

    session.add(convo)
    session.commit()
    session.refresh(convo)
    return convo


@router.post("/{conversation_id}/message", description="""To send messages/human prompts
                                            to LLM through API and recieve a response.
                                            we also count prompt and completion tokens
                                            and store them in conversations table SQLite.
                                            """)
def send_message(conversation_id: str, message:Message, session: SessionDep):
    
    convo = session.get(ConversationCreate, conversation_id)
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    agent = session.get(AgentCreate, convo.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    graph = graphs[conversation_id]
    if not graph:
        # fallback or raise
        raise HTTPException(status_code=500, detail="Graph not found in memory.")

    conv_config = {"configurable": {"thread_id": conversation_id}}
    graph = create_graph(f'{agent.name}_db', agent.creativity)

    res = stream_graph_updates(message.text,
                               conv_config,
                               graph)
    
    response_content = res['chatbot']['messages'][-1].content

    # saved datetime alongside the message.
    dt = res['chatbot']['messages'][-1].additional_kwargs['timestamp'].strftime("%Y-%m-%d %H:%M:%S %Z")

    tokens_usage = res['chatbot']['messages'][-1].additional_kwargs['tokens_usage']['token_usage']
                   
    # we have access to total tokens
    convo.total_tokens += tokens_usage['prompt_tokens']
    convo.total_tokens += tokens_usage['completion_tokens']

    return {"user": (message.text, tokens_usage['prompt_tokens']),
            "assistant": (response_content, tokens_usage['completion_tokens']),
            "timestamp": dt}


@router.get("/", response_model=List[ConversationCreate],
             description="""NOTE conversations don't store messages,
             messages are stored in graph SQLiteDB
             for the sake of memory-aware conversation with LLM.
             conversation stores associated agent's ID, tokens utilized.""")
def get_all_conversations(session: SessionDep,
                          offset: int = 0,
                          limit: Annotated[int, Query(le=100)] = 100
                          ):
    conversations = session.exec(select(ConversationCreate).offset(offset).limit(limit)).all()
    return conversations

@router.get("/{conversation_id}", response_model=Conversation,
            description="To grab a single conversation.")
def get_conversation(conversation_id: str, session: SessionDep):
    conversation = session.get(ConversationCreate, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation

@router.get("/{conversation_id}/messages",
            description="To grab all message of a conversation.")
def get_conversation_messages(conversation_id: str, session: SessionDep):

    convo = session.get(ConversationCreate, conversation_id)
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    agent = session.get(AgentCreate, convo.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    conv_config = {"configurable": {"thread_id": conversation_id}}
    graph = create_graph(f'{agent.name}_db', agent.creativity)
    
    snapshot = graph.get_state(conv_config)

    return snapshot.values['messages']



@router.delete("/{conversation_id}",
               description="To delete a conversation by its ID.")
def delete_conversation(conversation_id: str, session: SessionDep):
    conversation = session.get(ConversationCreate, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    session.delete(conversation)
    session.commit()
    return "Conversation deleted."


