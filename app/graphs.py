import os
from typing import Annotated, TypedDict
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage, HumanMessage,SystemMessage
from langchain_groq import ChatGroq
from langchain_tavily import TavilySearch as TavilySearchResults

from langgraph.prebuilt import tools_condition
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from app.rag import retriver, get_retriever

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
model_name = os.getenv("MODEL_NAME")

from  langchain_groq import ChatGroq
model = ChatGroq(
    api_key=api_key,
    model_name=model_name,
    max_tokens=500,
    temperature=0.0,
)

search_tool = TavilySearchResults(
    max_results=2,
    description="Search the web for real-time information."
    )

@tool
def rag_tool(query):
    """
    Retrieve relevant information from all uploaded PDF documents.
    Use this tool whenever the user asks questions, seeks facts, 
    or inquires about any uploaded or stored PDF files.
    """
    current_retriever = get_retriever()
    if current_retriever is None:                    
        return "No relevant information found in the uploaded documents."
    
    docs=current_retriever.invoke(query)
    if not docs:
        return "No matching information found in the uploaded documents."

    formatted = []

    for doc in docs:
        file = doc.metadata.get("filename", "Unknown File")
        page = doc.metadata.get("page", "Unknown Page")
        formatted.append(f"[File: {file} | Page: {page}]\n{doc.page_content}")
    
    return "\n\n".join(formatted)

tools = [search_tool,rag_tool]

llm_with_tools=model.bind_tools(tools)


class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

def chat_node(state: ChatState):

    messages = state['messages']

    system_prompt = SystemMessage(
        content=(
            "You are a helpful AI assistant with access to tools. "
            "You MUST use the 'search_tool' for any real-time news, current events, or web queries. "
            "You MUST use the 'rag_tool' whenever the user asks questions about documents or files."
            "When answering questions from documents, always mention the source filename and page number where you found the information."
        )
    )
    full_messages = [system_prompt] + messages
    response = llm_with_tools.invoke(full_messages)
    return {'messages': [response]}

tool_node=ToolNode(tools)

graph=StateGraph(ChatState)

graph.add_node('chat_node',chat_node)

graph.add_node('tools', tool_node)

graph.add_edge(START,'chat_node')
graph.add_conditional_edges(
    'chat_node',tools_condition
)
graph.add_edge('tools','chat_node')

# app_graph = graph.compile()

