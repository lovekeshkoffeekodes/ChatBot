import os
from typing import Annotated, TypedDict
from dotenv import load_dotenv

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_groq import ChatGroq
from langchain_community.tools.tavily_search import TavilySearchResults

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

load_dotenv()

search_tool = TavilySearchResults(max_results=2)
tools = [search_tool]

api_key = os.getenv("GROQ_API_KEY")
model_name = os.getenv("MODEL_NAME")

from  langchain_groq import ChatGroq
model = ChatGroq(
    api_key=api_key,
    model_name=model_name,
    max_tokens=500,
    temperature=0.0,
).bind_tools(tools)

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

def chat_node(state: ChatState):

    messages = state['messages']
    response = model.invoke(messages)
    return {'messages': [response]}

def should_continue(state:ChatState):
    messages = state['messages']
    last_message = messages[-1]

    if last_message.tool_calls:
        return "tools"
    
    return END

graph=StateGraph(ChatState)

graph.add_node('chat_node',chat_node)
tool_node = ToolNode(tools=tools)
graph.add_node('tools', tool_node)

graph.add_edge(START,'chat_node')
graph.add_conditional_edges(
    'chat_node',
    should_continue,
    {
        "tools": "tools",
        END: END
    }
)
graph.add_edge('tools','chat_node')

# chatbot=graph.compile


# def retrieve_all_thread():
#     all_thread=set()
#     for checkpoint in checkpointer.list(None):
#         all_thread.add(checkpoint.config['configurable']['thread_id'])

#     return list(all_thread)