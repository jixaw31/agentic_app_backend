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

try:
    os.mkdir('conversations_db')
except:
    os.path.isdir('conversations_db')

conn = sqlite3.connect('conversations_db/database.db', check_same_thread=False)
checkpointer = SqliteSaver(conn)

class State(TypedDict):
    sender: str  # 'user' or 'assistant'
    text: str
    tokens: int
    timestamp: datetime = Field(default_factory=datetime.now(timezone.utc))
    messages: Annotated[list, add_messages]

graph_builder = StateGraph(State)

# Set up Cohere API key
os.environ["DEEPSEEK_API_KEY"] = os.getenv("DEEPSEEK_API_KEY")

llm = ChatDeepSeek(
    model="deepseek-chat",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)


def chatbot(state: State):
    return {"messages": [llm.invoke(state["messages"])]}

# nodes
graph_builder.add_node("chatbot", chatbot)

# edges
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)

graph = graph_builder.compile(checkpointer=checkpointer)



def stream_graph_updates(user_input: str, conv_config):
    for event in graph.stream({"messages": [("user", user_input)]}, conv_config):
        for value in event.values():
            res = value["messages"][-1]
            return res.content,\
                   res.response_metadata['token_usage']['prompt_tokens'],\
                   res.response_metadata['token_usage']['completion_tokens'],
                   

