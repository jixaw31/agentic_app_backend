from langchain_mcp_adapters.client import MultiServerMCPClient, ClientSession
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition
import  os, asyncio
import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langchain_core.messages import AIMessage
from dotenv import load_dotenv
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from datetime import datetime, timezone
from langgraph.types import Command, interrupt
from groq import NotFoundError


# print(tools_list)
load_dotenv()

os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.1,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    )

client = MultiServerMCPClient(
    {
        "med_tools": {
            "command": "python",
            # Make sure to update to the full absolute path to your math_server.py file
            "url":"http://localhost:8001/mcp",
            "transport": 'streamable_http',
        },
        # "medRxiv": {
        #     "command": "python",
        #     # Make sure to update to the full absolute path to your math_server.py file
        #     "url":"http://localhost:8002/mcp",
        #     "transport": 'streamable_http',
        # }
    }
)



@tool
def human_assistance(query: str) -> str:
    """Request assistance from a human."""
    human_response = interrupt({"query": query})
    return human_response["data"]


# a function to create graph for each conversation
async def create_graph(checkpointer,
                       convo_db_name:str,
                    #    tools_list,
                       creativity:float = 0.1):

    try:
        tools_list = await client.get_tools()

    except httpx.ConnectError:
        print("Unable to connect to the MCP server. Please make sure it is running.")
        tools_list = []
    except httpx.HTTPStatusError as e:
        print(f"Server returned an error: {e.response.status_code} - {e.response.text}")
        tools_list = []
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        tools_list = []
    
    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=creativity,
        max_tokens=None,
        timeout=None,
        max_retries=2,
    )

    async def query_or_respond(state: MessagesState):
        """Generate tool call for retrieval or respond."""
        
        # # Define your system message
        # system_message = SystemMessage(
        #     content=(
        #         "Only call tools and don't generate anything else."
        #     )
        # )

        # # Prepend the system message to the user's message history
        # messages = [system_message] + state["messages"]

        llm_with_tools = llm.bind_tools(tools_list)
        
        
        try:
            # Try getting a response from the LLM
            response = await llm_with_tools.ainvoke(state["messages"])
            
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

    
    # Step 2: Execute the retrieval.
    mcp_tool_nodes = ToolNode(tools_list, name="mcp_tools")

    # Step 3: Generate a response using the retrieved content.
    async def generate(state: MessagesState):
        """Generate answer."""

        # Get generated ToolMessages
        recent_tool_messages = []
        for message in reversed(state["messages"]):
            if message.type == "tool":
                recent_tool_messages.append(message)
            else:
                break
        tool_messages = recent_tool_messages[::-1]
        # Format into prompt
        
        docs_content = "\n\n".join(doc.content for doc in tool_messages)

        system_message_content = (
            "You are an assistant for question-answering tasks. "
            "Use the following pieces of retrieved context to answer "
            "the question. If you don't know the answer, say that you "
            "don't know. Use three sentences maximum and keep the "
            "answer concise."
            "\n\n"
            f"{docs_content}"
        )
        conversation_messages = [
            message
            for message in state["messages"]
            if message.type in ("human", "system")
            or (message.type == "ai" and not message.tool_calls)
        ]
        prompt = [SystemMessage(system_message_content)] + conversation_messages

        # Run
        llm_with_human_assistance = llm.bind_tools([human_assistance])
        response = await llm_with_human_assistance.ainvoke(prompt)
        return {"messages": [response]}
    
    
    # defining human_assistant tool node
    human_assistance_tool_node = ToolNode([human_assistance], name="human_assistance")


    graph_builder = StateGraph(MessagesState)

    graph_builder.add_node(query_or_respond)
    graph_builder.add_node(mcp_tool_nodes)
    graph_builder.add_node(human_assistance_tool_node)
    graph_builder.add_node(generate)

    graph_builder.set_entry_point("query_or_respond")
    graph_builder.add_conditional_edges(
        "query_or_respond",
        tools_condition,
        {END: END, "mcp_tools": "mcp_tools"},
    )
    graph_builder.add_edge("mcp_tools", "generate")
    graph_builder.add_conditional_edges(
        "generate",
        tools_condition,
        {END: END, "human_assistance": "human_assistance"},
    )
    graph_builder.add_edge("human_assistance", END)
    

    graph = graph_builder.compile(checkpointer=checkpointer)
 
    return graph

  
# calling the memory-aware graph
async def stream_graph_updates(user_input: str, conv_config, graph):

    async for event in graph.astream({"messages": [("user", user_input)]},
                                        conv_config,
                                        # stream_mode="messages"
                                        ):
        return event

    # async for token, metadata in graph.astream({"messages": [("user", user_input)]},
    #                                     conv_config,
    #                                     stream_mode="messages"):
    #     print("Token", token)
    #     print("Metadata", metadata)
    #     print("\n")

# async def stream_graph_updates(user_input: str, conv_config, graph):
#     async for message_chunk, metadata in graph.astream(
#         {"messages": [("user", user_input)]},
#         conv_config,
#         stream_mode="messages"
#     ):
#         if message_chunk and hasattr(message_chunk, "content"):
#             print(message_chunk.content, end="", flush=True)

# # third one
# async def stream_graph_updates(user_input: str, conv_config, graph):
#     async for message_chunk, metadata in graph.astream(
#         {"messages": [("user", user_input)]},
#         conv_config,
#         stream_mode="messages"
#     ):
#         if hasattr(message_chunk, "content") and message_chunk.content:
#             yield message_chunk.content
