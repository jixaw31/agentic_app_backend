from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlmodel import SQLModel
from persistDB import engine
from agents import router as agents_router
from conversations import router as conversations_router
from files import router as files_router

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("App startup: creating DB tables...")
    create_db_and_tables()
    yield
    print("App shutdown: cleanup logic if needed.")

app = FastAPI(lifespan=lifespan)

# app.include_router(agents_0_router, prefix="/agents_0", tags=["Agents_0"])
app.include_router(agents_router, prefix="/agents", tags=["Agents"])
app.include_router(conversations_router, prefix="/conversations", tags=["Conversations"])
app.include_router(files_router, prefix="/conversations", tags=["Files"])

