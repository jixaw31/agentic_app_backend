from typing import Annotated
from typing_extensions import TypedDict
from io import BufferedReader

from langchain_cohere import ChatCohere
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, ToolMessage, AIMessage

import os

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
# from langgraph.prebuilt import ToolNode, tools_condition

from langchain_core.prompts import ChatPromptTemplate
from langchain_deepseek import ChatDeepSeek

import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
import os

from datetime import datetime, timezone
from pydantic import Field

# Set up DeepSeek API key
os.environ["DEEPSEEK_API_KEY"] = os.getenv("DEEPSEEK_API_KEY")

def create_graph(convo_db_name:str, creativity:float):
    try:
        os.mkdir(convo_db_name)
    except:
        os.path.isdir(convo_db_name)
    
    conn = sqlite3.connect(f'{convo_db_name}/database.db', check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    class State(TypedDict):
        # sender: str  # 'user' or 'assistant'
        # text: str
        # tokens: int
        # timestamp: datetime = Field(default_factory=datetime.now(timezone.utc))
        messages: Annotated[list, add_messages]

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
            additional_kwargs={"timestamp": datetime.now(timezone.utc),
                               "tokens_usage":response.response_metadata} # to calculate the tokens
        )

        return {"messages": [response_with_ts]}

    # nodes
    graph_builder.add_node("chatbot", chatbot)

    # edges
    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_edge("chatbot", END)

    graph = graph_builder.compile(checkpointer=checkpointer)

    return graph



def stream_graph_updates(user_input: str, conv_config, graph):
    # could be written better
    for event in graph.stream({"messages": [("user", user_input)]},
                               conv_config):
        
        return event
    
