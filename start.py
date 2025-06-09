# start.py
import threading
import subprocess
import uvicorn

def run_mcp():
    subprocess.Popen(["python", "mcp_servers\run_mcp_servers.py"])

# Start MCP in the background
threading.Thread(target=run_mcp, daemon=True).start()

# Start FastAPI server (replace with your app and port if needed)
uvicorn.run("main:app", host="0.0.0.0", port=8000)