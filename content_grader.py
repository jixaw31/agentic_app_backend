from langgraph.graph import StateGraph, MessagesState, START, END
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

llm = ChatGroq(
    model="llama3-70b-8192",  # or llama3-70b-8192, etc., depending on your Groq model
    temperature=0.1,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    # verbose=True or False, as needed
    )
async def grader(state: MessagesState):
        class GradeContents(BaseModel):
            """Binary score for relevance check on retrieved documents."""
            binary_score: str = Field(
                description="Retrieved contents from pubmed are relevant to the question, 'yes' or 'no'"
            )
        
        # LLM with function call
        structured_llm_grader = llm.with_structured_output(GradeContents)

        # Prompt
        system = """You are a grader assessing relevance of a retrieved content to a user question. \n 
            If the document contains keyword(s) or semantic meaning related to the user question, grade it as relevant. \n
            Only respond with 'yes' or 'no'. """

        grade_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system),
                ("human", "Retrieved content: \n\n {content} \n\n User question: {question}"),
            ]
        )

        retrieval_grader = grade_prompt | structured_llm_grader

        question = "home remedy for common cold?"
        
        grader_res = await retrieval_grader.ainvoke({"question": question,
                                                    "content": state["messages"]})
        print(grader_res)
        return grader_res