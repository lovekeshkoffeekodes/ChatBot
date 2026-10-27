
from fastapi import APIRouter, status, Request
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from app.database import get_db

print("==========START==========")

router = APIRouter(prefix="/chat/stream", tags=["jobs"])

class ChatRequest(BaseModel):
    messages: str
    thread_id: str
    chat_title: str = "New Chat"


async def ChatStream(request: Request, body: ChatRequest):
    return {"message": "Hello From Chat Stream"}

router.add_api_route(
    "",
    ChatStream,
    methods=["POST"],
    status_code=status.HTTP_202_ACCEPTED,
    name="ChatStream",
)


@router.post("/test")
async def ChatTest(request: Request, body: ChatRequest):
    print("=============STEP 1=============")
    print("Request:", body)

    compiled_graph = request.app.state.compiled_graph

    async with get_db() as conn:

        # --- 1. Get or create the conversation for this thread_id ---
        row = await conn.execute(
            "SELECT id FROM conversations WHERE thread_id = %s",
            [body.thread_id]
        )
        conversation = await row.fetchone()

        if conversation is None:
            # First time this thread_id is used — create a new conversation
            new_conv = await conn.execute(
                """
                INSERT INTO conversations (thread_id, chat_title)
                VALUES (%s, %s)
                RETURNING id
                """,
                [body.thread_id, body.chat_title]
            )
            conversation_row = await new_conv.fetchone()
            conversation_id = conversation_row[0]
            print(f"New conversation created: id={conversation_id}")
        else:
            conversation_id = conversation[0]
            print(f"Existing conversation found: id={conversation_id}")
            # Update title in case it was just generated (was "New Chat" before)
            await conn.execute(
                "UPDATE conversations SET chat_title = %s WHERE id = %s",
                [body.chat_title, conversation_id]
            )

        # --- 2. Save the human message ---
        await conn.execute(
            """
            INSERT INTO messages (conversation_id, role, content)
            VALUES (%s, %s, %s)
            """,
            [conversation_id, "human", body.messages]
        )
        print("Human message saved.")

        # --- 3. Invoke LangGraph ---
        state = await compiled_graph.ainvoke(
            {"messages": [HumanMessage(content=body.messages)]},
            config={"configurable": {"thread_id": body.thread_id}}
        )

        # --- 4. Extract and save the AI reply ---
        ai_reply = state["messages"][-1].content
        await conn.execute(
            """
            INSERT INTO messages (conversation_id, role, content)
            VALUES (%s, %s, %s)
            """,
            [conversation_id, "ai", ai_reply]
        )
        print("AI reply saved.")

    return {
        "thread_id": body.thread_id,
        "conversation_id": conversation_id,
        "reply": ai_reply
    }


@router.get("/threads")
async def get_all_threads(request: Request):
    """Return all conversations from our custom conversations table."""
    async with get_db() as conn:
        rows = await conn.execute(
            """
            SELECT thread_id, chat_title, created_at
            FROM conversations
            ORDER BY created_at DESC
            """
        )
        conversations = await rows.fetchall()

    return {
        "threads": [
            {
                "thread_id": c[0],
                "chat_title": c[1],
                "created_at": str(c[2])
            }
            for c in conversations
        ]
    }



@router.get("/history/{thread_id}")
async def get_history(thread_id: str, request: Request):
    """Read chat history from our custom messages table."""
    async with get_db() as conn:
        row = await conn.execute(
            "SELECT id FROM conversations WHERE thread_id = %s",
            [thread_id]
        )
        conversation = await row.fetchone()

        if conversation is None:
            return {"messages": [], "detail": "No conversation found for this thread_id"}

        conversation_id = conversation[0]

        rows = await conn.execute(
            """
            SELECT role, content, created_at
            FROM messages
            WHERE conversation_id = %s
            ORDER BY created_at ASC
            """,
            [conversation_id]
        )
        messages = await rows.fetchall()

    return {
        "thread_id": thread_id,
        "messages": [
            {"role": m[0], "content": m[1], "created_at": str(m[2])}
            for m in messages
        ]
    }