from fastapi import APIRouter, Request, HTTPException, Depends, Query
from models import *
from dotenv import load_dotenv
import os, asyncpg
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from typing import Annotated
from sqlmodel import select
from sql_models import AgentCreate, ConversationCreate
from persistDB import AsyncSessionDep
# from persistDB import AsyncSessionDep
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, ToolMessage, AIMessage
# from graph import stream_graph_updates, create_graph
from models import ConversationRead, Conversation
from test_mcp_1 import create_graph, stream_graph_updates


load_dotenv() 

router = APIRouter()


@router.post(
    "/", 
    response_model=Conversation,  # Make sure this model exists and includes all required fields.
    description="""To create a conversation, by employing a certain agent (grabbing agent by ID)."""
)
async def start_conversation(request: NewConversationRequest, session: AsyncSessionDep,
                            #  offset: int = 0,
                            #  limit: Annotated[int, Query(le=100)] = 100,
                             ):
    
    # agent = await session.get(AgentCreate, "acf3c31d-fa74-4f0f-811d-798106681d60")
    statement = select(AgentCreate).where(AgentCreate.name == "medical agent")
    results = await session.execute(statement)
    agent = results.scalars().first()

    if not agent:
        raise HTTPException(status_code=404, detail="Provide agent ID")

    today = datetime.now().strftime("%A, %B %d, %Y")
    agent.systemPrompt = f"{agent.systemPrompt}\n\nToday is {today}."

    naive_now = datetime.now(timezone.utc).replace(tzinfo=None)
    convo = ConversationCreate(
        agent_id=agent.id,
        title=request.title,
        created_at = naive_now,
    )

    x = '_'.join(convo.title.split(' ')[:3])
    
    conv_config = {"configurable": {"thread_id": convo.id}}
    
    system_message = [SystemMessage(content=agent.systemPrompt)]
    welcome_message = [AIMessage(content=agent.welcomeMessage)]

    DB_URI = os.getenv("DB_URI")

    # 🧠 Check if 'checkpoints' table exists
    # conn = await asyncpg.connect(dsn=DB_URI)
    # try:
    #     exists = await conn.fetchval("""
    #         SELECT EXISTS (
    #             SELECT FROM information_schema.tables 
    #             WHERE table_name = 'checkpoints'
    #         )
    #     """)
    # finally:
    #     await conn.close()


    async with AsyncPostgresSaver.from_conn_string(os.getenv("DB_URI")) as checkpointer:

        await checkpointer.setup() # Need to apply only once, and it does it.
        # if not exists:
        #     await checkpointer.setup()
        #     print("✅ 'checkpoints' table created.")
        # else:
        #     print("ℹ️ 'checkpoints' table already exists.")
        
        graph = await create_graph(checkpointer,
                                    convo.title,
                                    creativity=agent.creativity,
                                   )
    
        await graph.aupdate_state(conv_config, {"messages": system_message}, as_node="query_or_respond")

        # await graph.aupdate_state(conv_config, {"messages": welcome_message}, as_node="query_or_respond")

    session.add(convo)
    await session.commit()
    await session.refresh(convo)
    await session.refresh(agent)  

    return convo



@router.post("/{conversation_id}/message", description="""To send messages/human prompts
                                            to LLM through API and receive a response.
                                            We also count prompt and completion tokens
                                            and store them in conversations table SQLite.
                                            """)
async def send_message(conversation_id: str, message: Message, session: AsyncSessionDep,
                       ):
    
    convo = await session.get(ConversationCreate, conversation_id)
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    agent = await session.get(AgentCreate, convo.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    conv_config = {"configurable": {"thread_id": conversation_id}}

    # tools_list = await client.get_tools()

    async with AsyncPostgresSaver.from_conn_string(os.getenv("DB_URI")) as checkpointer:
        
        
        graph = await create_graph(checkpointer,
                                    convo.title,
                                    # tools_list,
                                    creativity=agent.creativity,
                                   )

        if not graph:
            raise HTTPException(status_code=500, detail="Graph not found in memory.")

        res = await stream_graph_updates(message.text, conv_config, graph)
        print(res)
    response_content = res['query_or_respond']['messages'][-1].content

    if "Connection issue" in response_content:
        return {"assistant": response_content}
    else:
        dt = res['query_or_respond']['messages'][-1].additional_kwargs['timestamp'].strftime("%Y-%m-%d %H:%M:%S %Z")
        tokens_usage = res['query_or_respond']['messages'][-1].additional_kwargs['tokens_usage']['token_usage']
                    
        convo.total_tokens += tokens_usage['prompt_tokens']
        convo.total_tokens += tokens_usage['completion_tokens']

        # Save updated total_tokens back to DB
        session.add(convo)
        await session.commit()

        return {
            "user": (message.text, tokens_usage['prompt_tokens']),
            "assistant": (response_content, tokens_usage['completion_tokens']),
            "timestamp": dt
        }

    

@router.get("/",
             description="""NOTE conversations don't store messages,
             messages are stored in graph SQLiteDB
             for the sake of memory-aware conversation with LLM.
             conversation stores associated agent's ID, tokens utilized.""")
async def get_all_conversations(session: AsyncSessionDep,
                                offset: int = 0,
                                limit: Annotated[int, Query(le=100)] = 100
                                )-> list[ConversationRead]:
    
    results = await session.execute(
    select(ConversationCreate).order_by(ConversationCreate.created_at.desc())
    )
    conversations = results.scalars().all()
    
    return conversations



@router.get("/{conversation_id}", response_model=Conversation,
            description="To grab a single conversation.")
async def get_conversation(conversation_id: str, session: AsyncSessionDep):
    conversation = session.get(ConversationCreate, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.get("/{conversation_id}/messages",
            description="To grab all message of a conversation.")
async def get_conversation_messages(conversation_id: str, session: AsyncSessionDep):

    convo = await session.get(ConversationCreate, conversation_id)
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    agent = await session.get(AgentCreate, convo.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    conv_config = {"configurable": {"thread_id": conversation_id}}

    

    async with AsyncPostgresSaver.from_conn_string(os.getenv("DB_URI")) as checkpointer:
        graph = await create_graph(checkpointer, convo.title, agent.creativity)

        snapshot = await graph.aget_state(conv_config)

        # Filter out messages of type 'system' and 'tool'
        filtered_messages = [
            msg for msg in snapshot.values['messages']
            if msg.type not in ("system", "tool")
        ]

        return filtered_messages



@router.delete("/{conversation_id}",
               description="To delete a conversation by its ID.")
async def delete_conversation(conversation_id: str, session: AsyncSessionDep):
    conversation = await session.get(ConversationCreate, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    await session.delete(conversation)  # Optional: SQLAlchemy sometimes allows this without await
    await session.commit()              

    return {"detail": "Conversation deleted."}


