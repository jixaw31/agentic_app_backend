#!/bin/bash
# start.sh

# Start MCP servers in the background
python mcp_servers\run_mcp_servers.py &

# Start FastAPI app
uvicorn main:app --host 0.0.0.0 --port=8000 --reload