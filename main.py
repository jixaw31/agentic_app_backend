from fastapi import FastAPI
from agents import router as agents_router
from conversations import router as conversations_router
from files import router as files_router


app = FastAPI()


app.include_router(agents_router, prefix="/agents", tags=["Agents"])
app.include_router(conversations_router, prefix="/conversations", tags=["Conversations"])
app.include_router(files_router, prefix="/conversations", tags=["Files"])

