from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from groq import NotFoundError
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import AIMessage
from langchain_groq import ChatGroq
import os
from fastapi.concurrency import run_in_threadpool
from datetime import timezone, datetime
from dotenv import load_dotenv
load_dotenv()


# model = init_chat_model(model="anthropic:claude-3-5-haiku-latest")

DB_URI = os.getenv("DB_URI")


# a function to create graph for each conversation
async def create_graph(checkpointer, convo_db_name:str, creativity:float = 0.0):
    
    # await checkpointer.setup() # 


    # default typing in LangChain/LangGraph
    class State(TypedDict):
        
        # to prevent overwriting messages and adding them sequentially
        messages: Annotated[list, add_messages]
        
    # initiating the graph
    graph_builder = StateGraph(State)

    llm = ChatGroq(

    model="llama-3.1-8b-instant",  # or llama3-70b-8192, etc., depending on your Groq model
    temperature=creativity,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    # verbose=True or False, as needed
    )


    async def chatbot(state: State):
        try:
            # Try getting a response from the LLM
            response = await llm.ainvoke(state["messages"])
            
            response_with_ts = AIMessage(
                content=response.content,
                additional_kwargs={
                    "timestamp": datetime.now(timezone.utc),
                    "tokens_usage": response.response_metadata
                }
            )
            return {"messages": [response_with_ts]}
        
        except NotFoundError:
            # Handle 404 from Groq
            error_message = AIMessage(
                content="❌ Connection issue: the model or endpoint was not found. Please try again later.",
                additional_kwargs={"timestamp": datetime.now(timezone.utc)}
            )
            return {"messages": [error_message]}
    
        except Exception as e:
            # Catch-all for other errors
            error_message = AIMessage(
                content="⚠️ An unexpected error occurred. Please try again.",
                additional_kwargs={
                    "timestamp": datetime.now(timezone.utc),
                    "error_details": str(e)  # optional: you can log this or hide it
                }
            )
            return {"messages": [error_message]}

    # nodes for now we have only one node, could be much more depending on the application
    graph_builder.add_node("chatbot", chatbot)

    # edges, we also can add a lot of edges depending on usecase
    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_edge("chatbot", END)

    # graph compiling, now we have access to graph
    graph = graph_builder.compile(checkpointer=checkpointer)

    return graph
    


# calling the memory-aware graph
async def stream_graph_updates(user_input: str, conv_config, graph):

        async for event in graph.astream({"messages": [("user", user_input)]},
                                            conv_config):
            return event



