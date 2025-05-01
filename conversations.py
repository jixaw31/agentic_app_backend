from fastapi import APIRouter, HTTPException, Depends
from models import *
from typing import Dict, List
from agents import agents_db
from dotenv import load_dotenv
from langchain_deepseek import ChatDeepSeek
from langchain_core.prompts import ChatPromptTemplate
import os

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
        (
            "system",
            agent.systemPrompt,
        ),
        ("human", "{input}"),
    ]
    )

    chain = prompt | llm

    res = chain.invoke(
        {
            "input": input_,
        }
    )
    return res.content,\
           res.response_metadata['token_usage']['completion_tokens'],\
           res.response_metadata['token_usage']['prompt_tokens']


# def get_tokens(text: str) -> int:
#     return max(1, int(len(text.split()) / 0.75))  # Rough estimate

# def generate_response(agent: Agent, history: List[Message], user_input: str) -> str:

#     return f"{agent.name} says: how can I help with: {user_input}'."


@router.post("/", response_model=Conversation)
def start_conversation(request: NewConversationRequest):
    if request.agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")

    convo = Conversation(agent_id=request.agent_id)
    welcome = agents_db[request.agent_id].welcomeMessage
    welcome_message = Message(
        sender="assistant",
        text=welcome,
        tokens= 0 # hard coded, since we pass the welcome message.
    )
    convo.messages.append(welcome_message)
    conversations_db[convo.id] = convo
    return convo

@router.post("/{conversation_id}/message", response_model=Conversation)
def send_message(conversation_id: str, message: UserMessage):
    convo = conversations_db.get(conversation_id)
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")

    agent = agents_db.get(convo.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    res_content, completion_tokens, prompt_tokens = generate_response_calc_token(message.text,
                                                                                 agent,
                                                                                 convo.messages)
    # user_tokens = get_tokens(message.text)
    convo.messages.append(Message(sender="user", text=message.text, tokens=prompt_tokens))
    convo.total_tokens += prompt_tokens

    # response_text = generate_response(agent, convo.messages, message.text)
    # response_tokens = get_tokens(response_text)
    convo.messages.append(Message(sender="assistant", text=res_content, tokens=completion_tokens))
    convo.total_tokens += completion_tokens

    return convo

@router.get("/{conversation_id}", response_model=Conversation)
def get_conversation(conversation_id: str):
    convo = conversations_db.get(conversation_id)
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return convo

@router.get("/agent/{agent_id}", response_model=List[Conversation])
def list_agent_conversations(agent_id: str):
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    return [c for c in conversations_db.values() if c.agent_id == agent_id]
