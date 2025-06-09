from langchain_mcp_adapters.client import MultiServerMCPClient




client = MultiServerMCPClient(
    {
        "pubmed": {
            "command": "python",
            # Make sure to update to the full absolute path to your math_server.py file
            "url":"http://localhost:8001/mcp",
            "transport": "streamable-http",
        },
        "medRxiv": {
            "command": "python",
            # Make sure to update to the full absolute path to your math_server.py file
            "url":"http://localhost:8002/mcp",
            "transport": "streamable-http",
        }
    }
)

async def get_tools():
    tools_list = await client.get_tools()
    return tools_list