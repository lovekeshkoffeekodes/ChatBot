
import os
from typing import Annotated, TypedDict
from dotenv import load_dotenv

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_groq import ChatGroq
from langchain_community.tools.tavily_search import TavilySearchResults

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
# from langgraph.checkpoint.sqlite import SqliteSaver
# import sqlite3
load_dotenv()
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel

router = APIRouter(prefix="/chat/stream", tags=["jobs"])
print("=============Hellooo What Happend ?=============")
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

# conn=sqlite3.connect(database='chatbot.db',check_same_thread=False)
# checkpointer=SqliteSaver(conn=conn)
# def init_feedback_db():
#     """Initializes the dedicated feedback table for analytics and user reviews."""
#     cursor = conn.cursor()

#     cursor.execute('''
#         CREATE TABLE IF NOT EXISTS feedback (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             thread_id TEXT NOT NULL,
#             message_index INTEGER NOT NULL,
#             rating INTEGER NOT NULL,
#             comment TEXT,
#             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#         )
#     ''')
#     conn.commit()

# init_feedback_db()

# def save_feedback(thread_id: str, message_index: int, rating: int, comment: str):
#     """Saves or updates user feedback for a specific assistant response."""
#     cursor = conn.cursor()
#     # Optional: check if feedback already exists for this message index to prevent duplicates
#     cursor.execute('''
#         INSERT INTO feedback (thread_id, message_index, rating, comment)
#         VALUES (?, ?, ?, ?)
#     ''', (thread_id, message_index, rating, comment))
#     conn.commit()

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

# chatbot=graph.compile(checkpointer=checkpointer)
chatbot=graph.compile()

# response=chatbot.invoke({'messages':["Explain Quantum Computing in one sentence."]})
# print(response)
class ChatRequest(BaseModel):
    message: str

async def ChatStream(body:ChatRequest):
    
    print("=============STEP 1=============")
    inputs = body
    print(inputs)
    response=chatbot.invoke({"messages":inputs.message})
    # print("Response:",response.content)
    print("Role:","assistant")
    return {"message":response}

router.add_api_route(
    "",
    ChatStream,
    methods=["POST"],
    status_code=status.HTTP_202_ACCEPTED,
    name="ChatStream",
)

# def retrieve_all_thread():
#     all_thread=set()
#     for checkpoint in checkpointer.list(None):
#         all_thread.add(checkpoint.config['configurable']['thread_id'])

#     return list(all_thread)