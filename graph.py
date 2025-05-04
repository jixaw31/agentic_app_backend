from typing import Annotated
from typing_extensions import TypedDict


from langchain_core.messages import AIMessage

import os

# importing built in nodes and edges
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from langchain_deepseek import ChatDeepSeek

import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

from datetime import datetime, timezone

from dotenv import load_dotenv
load_dotenv()

# Set up DeepSeek API key
os.environ["DEEPSEEK_API_KEY"] = os.getenv("DEEPSEEK_API_KEY")

# a function to create graph for each conversation
def create_graph(convo_db_name:str, creativity:float):

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

    # defining LLM
    llm = ChatDeepSeek(
        model="deepseek-chat",
        temperature = creativity,
        max_tokens=None,
        timeout=None,
        max_retries=2,
        # verbose= take Boolean value
    )

    def chatbot(state: State):
        
        # need to add a summarizer. for all the messages accumulated
        response = llm.invoke(state["messages"])
        
        response_with_ts = AIMessage(
            content=response.content,

            # adding any key arguments that we need, in this case tokens count and datetime
            additional_kwargs={"timestamp": datetime.now(timezone.utc),
                               "tokens_usage":response.response_metadata} # to calculate the tokens
        )

        return {"messages": [response_with_ts]}


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
    
