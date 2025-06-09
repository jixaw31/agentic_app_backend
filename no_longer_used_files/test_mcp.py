from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition
import asyncio, os, tiktoken, textwrap
from pprint import pprint
from langchain_core.output_parsers.string import StrOutputParser
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.chat_models import init_chat_model
from langchain_groq import ChatGroq
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

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


client = MultiServerMCPClient(
    {
        "pubmed": {
            # make sure you start your weather server on port 8000
            "url": "http://localhost:8000/mcp",
            "transport": "streamable_http",
        }
    }
)
async def main():
    tools = await client.get_tools()

    async def query_optimizer(state: MessagesState) -> MessagesState:
        system_message = """
            You are a biomedical research assistant with access to PubMed.
            Return five results.
            When a user asks a question, extract clear,
            concise search terms that reflect the medical topic and any relevant time frame
            (e.g., "best cure for cold in 2025" → "cold treatment" AND 2025). 
            Strip irrelevant or vague phrases, and prefer terminology used in scientific literature.
            Always include a year filter if mentioned. The result should be a PubMed-style search query.
            Only return the query.
        """
        re_write_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_message),
                (
                    "human",
                    "Here is the initial query: \n\n {query} \n only return the revised query.",
                ),
            ]
        )
        
        query = next(
            (msg.content for msg in reversed(state["messages"]) if isinstance(msg, HumanMessage)),
            None
        )
        question_rewriter = re_write_prompt | llm | StrOutputParser()
        response = await question_rewriter.ainvoke({"query": query})

        return {"messages": [HumanMessage(content=response)]}
    
    def call_model(state: MessagesState) -> MessagesState:

        response = llm.bind_tools(tools).invoke(state["messages"])
        return {"messages": response}
    
    async def final_rewriter(state: MessagesState) -> MessagesState:

        system_message = """
            You are a biomedical writing assistant tasked with rewriting informal or loosely phrased research findings into clear, professional, and scientifically grounded summaries.
            Your goals:
            - Maintain the core message of the original text.
            - Rephrase for clarity, formal tone, and scientific accuracy.
            - Add appropriate disclaimers when suggestions are based on anecdotal evidence or unverified remedies.
            - Avoid exaggeration or overstatement of efficacy.
            - If a medical remedy is mentioned, clarify whether it is supported by clinical evidence or commonly considered a home remedy.
            Output only the revised summary. Do not include explanations or additional commentary.
        """
        re_write_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_message),
                (
                    "human",
                    "Here is the initial output: \n\n {output} \n only return the revised output.",
                ),
            ]
        )
        
        output = next(
            (msg.content for msg in reversed(state["messages"]) if isinstance(msg, HumanMessage)),
            None
        )
        output_rewriter = re_write_prompt | llm | StrOutputParser()
        response = await output_rewriter.ainvoke({"output": output})

        return {"messages": [AIMessage(content=response)]}
    

    builder = StateGraph(MessagesState)

    builder.add_node(call_model)
    builder.add_node(ToolNode(tools))
    builder.add_node(query_optimizer)
    builder.add_node(final_rewriter)

    # builder.add_conditional_edges("call_model", call_model_condition)
    builder.add_edge(START, "query_optimizer")
    builder.add_edge("query_optimizer", "call_model")

    # builder.add_conditional_edges(
    #     "call_model",
    #     tools_condition,
    # )
    # builder.add_edge("tools", "call_model")
    builder.add_edge("call_model", "final_rewriter")
    builder.add_edge("final_rewriter", END)

    graph = builder.compile()

    user_input = "'What are some effective home remedies for the common cold in 2025?'"
    pmid = 28833689
    f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
    adad = 0
    async for event in graph.astream({"messages": [("user", user_input)]}):
        adad += 1
        for k, v in event.items():
            print(f"{adad}.{k.upper()} . . .\n")
            pprint(v)
        print("=" * 50)
        
    
    
if __name__ == "__main__":
    asyncio.run(main())