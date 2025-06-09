from typing import Annotated
from typing_extensions import TypedDict
# from langchain.chat_models import init_chat_model
# from langgraph.graph import StateGraph, MessagesState, START
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from groq import NotFoundError
from langchain_core.messages import AIMessage
from langchain_groq import ChatGroq
import os

# importing built in nodes and edges
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages


import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

from datetime import datetime, timezone

from dotenv import load_dotenv
load_dotenv()

# Set up DeepSeek API key
os.environ["DEEPSEEK_API_KEY"] = os.getenv("DEEPSEEK_API_KEY")
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

DB_URI = "postgresql://postgres:postgres@localhost:5442/postgres?sslmode=disable"

# a function to create graph for each conversation
def create_graph(convo_db_name:str, creativity:float = 0.0):

    # creating a directory to properly store the messages 
    try:
        os.mkdir(convo_db_name)
    except:
        os.path.isdir(convo_db_name)
    
    # connecting to a SQLite DB
    conn = sqlite3.connect(f'{convo_db_name}/database.db', check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    # default typing in LangChain/LangGraph
    class State(TypedDict):
        
        # to prevent overwriting messages and adding them sequentially
        messages: Annotated[list, add_messages]

    # initiating the graph
    graph_builder = StateGraph(State)

    llm = ChatGroq(

    model="llama3-70b-8192",  # or llama3-70b-8192, etc., depending on your Groq model
    temperature=creativity,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    # verbose=True or False, as needed
    )


    def chatbot(state: State):
        try:
            # Try getting a response from the LLM
            response = llm.invoke(state["messages"])
            
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
def stream_graph_updates(user_input: str, conv_config, graph):
    # could be written better
    for event in graph.stream({"messages": [("user", user_input)]},
                               conv_config):
        return event
    
