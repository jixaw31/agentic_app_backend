from fastapi import FastAPI
from agents import router as agents_router
from conversations import router as conversations_router
from files import router as files_router
from contextlib import asynccontextmanager
from sqlmodel import SQLModel
from persistDB import engine

# @asynccontextmanager
# async def lifespan(app):
#     yield

app = FastAPI(
    # lifespan=lifespan
    )

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

@app.on_event("startup")
def on_startup():
    create_db_and_tables()






# app.include_router(agents_0_router, prefix="/agents_0", tags=["Agents_0"])
app.include_router(agents_router, prefix="/agents", tags=["Agents"])
app.include_router(conversations_router, prefix="/conversations", tags=["Conversations"])
app.include_router(files_router, prefix="/conversations", tags=["Files"])

