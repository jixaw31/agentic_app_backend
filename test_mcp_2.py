from langchain_mcp_adapters.client import MultiServerMCPClient, ClientSession
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition
import asyncio, os, tiktoken, textwrap
from pprint import pprint
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_core.output_parsers.string import StrOutputParser
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from backend.mcp_servers.pubmed.pubmed_mcp_server import search_abstracts
from pydantic import BaseModel, Field
from langchain import hub
from mcp.client.stdio import stdio_client



load_dotenv()

os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")
llm = ChatGroq(

    model="llama3-70b-8192",  # or llama3-70b-8192, etc., depending on your Groq model
    temperature=0.1,
    max_tokens=512,
    timeout=None,
    max_retries=2,
    # verbose=True or False, as needed
    )


# client = MultiServerMCPClient(
#     {
#         "pubmed": {
#             "url": "http://localhost:8000/mcp",
#             "transport": "streamable-http",
#         }
#     }
# )

client = MultiServerMCPClient(
    {
        "pubmed": {
            "command": "python",
            # Make sure to update to the full absolute path to your math_server.py file
            "args": [r"C:\Users\jix\Desktop\the_assistant\backend\mcp_servers\pubmed_mcp_server.py"],
            "transport": "stdio",
        },
        "medRxiv": {
            "command": "python",
            # Make sure to update to the full absolute path to your math_server.py file
            "args": [r"C:\Users\jix\Desktop\the_assistant\backend\mcp_servers\medrxiv_mcp_server\medrxiv_server.py"],
            "transport": "stdio",
        }
    }
)

async def main():
    
    tools_list = await client.get_tools()
    # Create ToolNodes
    
    # tool_nodes = {
    # tool.name: ToolNode([tool])
    # for tool in tools_list
    # }
    # return "+" * 50

    # return ""
    # # Step 1: Generate an AIMessage that may include a tool-call to be sent.
    # async def query_or_respond(state: MessagesState):
    #     """Generate tool call for retrieval or respond."""
    #     llm_with_tools = llm.bind_tools(tools_list)
    #     response = await llm_with_tools.ainvoke(state["messages"])
    #     return {"messages": [response]}
    
    async def query_or_respond(state: MessagesState):
        """Generate tool call for retrieval or respond."""

        # Define your system message
        system_message = SystemMessage(
            content=(
                "Only call tool and mention the tool's name, don't generate anything else."
            )
        )

        # Prepend the system message to the user's message history
        # messages = [system_message] + state["messages"]
        
        llm_with_tools = llm.bind_tools(tools_list)
        response = await llm_with_tools.ainvoke(state["messages"])
        
        
        
        return {"messages": response}
    # resss = await query_or_respond({"messages": [{"role": "user", "content": "COVID 19 home remedy"}]})
    # # print(resss['messages'].content)
    # return ""
    # resss = await query_or_respond({"messages": [HumanMessage(content="what is aids?")]})
    # print(resss['messages'])
    # return resss

    # Step 2: Execute the retrieval.
    tool_node = ToolNode(tools_list)

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
        response = llm.invoke(prompt)
        return {"messages": [response]}
    
    
    graph_builder = StateGraph(MessagesState)

    graph_builder.add_node(query_or_respond)
    graph_builder.add_node(tool_node)
    graph_builder.add_node(generate)

    graph_builder.set_entry_point("query_or_respond")
    graph_builder.add_conditional_edges(
        "query_or_respond",
        tools_condition,
        {END: END, "tools": "tools"},
    )
    graph_builder.add_edge("tools", "generate")
    graph_builder.add_edge("generate", END)
    
    graph = graph_builder.compile()

    input_message = "COVID-19 vaccine efficacy"
    

    async for step in graph.astream(
        {"messages": [{"role": "user", "content": input_message}]},
        stream_mode="values",
    ):
    
        step["messages"][-1].pretty_print()

if __name__ == "__main__":
    asyncio.run(main())