from fastapi import Depends, HTTPException, Query
from sqlmodel import Field, Session, SQLModel, create_engine, select
from sqlmodel import SQLModel, Field
from sqlmodel import SQLModel, Field, Relationship
from typing import Annotated


engine = create_engine("sqlite:///agents_database.db",
                       connect_args={"check_same_thread": False})

# def create_db_and_tables():
#     SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]