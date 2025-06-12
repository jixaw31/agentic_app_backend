from fastapi_mcp import FastApiMCP
from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlmodel import SQLModel
# from persistDB import engine
from agents import router as agents_router
from conversations import router as conversations_router
from files import router as files_router
from fastapi.middleware.cors import CORSMiddleware
from persistDB import init_db
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
# from get_tools_list import load_tools
from users import router as auth_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("App startup: creating DB tables...")
    # create_db_and_tables()
    await init_db()


    yield
    print("App shutdown: cleanup logic if needed.")


app = FastAPI(lifespan=lifespan)


# Allow frontend access (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js frontend
        "http://127.0.0.1:3000",  # Just in case browser treats this differently
        "https://nextjs-agentic-app.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# app.include_router(agents_0_router, prefix="/agents_0", tags=["Agents_0"])
app.include_router(agents_router, prefix="/agents", tags=["Agents"])
app.include_router(auth_router, prefix="/auth", tags=["Users"])
app.include_router(conversations_router, prefix="/conversations", tags=["Conversations"])
app.include_router(files_router, prefix="/conversations", tags=["Files"])
