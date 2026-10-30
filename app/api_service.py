
from fastapi import APIRouter, status, Request,UploadFile, File,HTTPException
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from app.database import get_db
import tempfile
import os
from app.rag import process_pdf  

print("==========START==========")

router = APIRouter(prefix="")

class ChatRequest(BaseModel):
    messages: str
    thread_id: str
    chat_title: str = "New Chat"

@router.post("/chat/stream")
async def ChatStream(request: Request, body: ChatRequest):
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

# router.add_api_route(
#     "/chat/stream",
#     ChatStream,
#     methods=["POST"],
#     status_code=status.HTTP_202_ACCEPTED,
#     name="ChatStream",
# )

@router.get("/conversations")
async def get_all_threads(request: Request):
    """Return all conversations from our custom conversations table."""
    async with get_db() as conn:
        rows = await conn.execute(
            """
            SELECT thread_id, chat_title, created_at
            FROM conversations
            WHERE is_deleted = FALSE
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

@router.get("/conversations/{thread_id}/messages")
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

# --- Pydantic model for updating title ---
class UpdateTitleRequest(BaseModel):
    chat_title: str

@router.patch("/conversations/{thread_id}")
async def update_chat_title(thread_id: str, body: UpdateTitleRequest):
    """Edit the chat title for a specific thread."""
    async with get_db() as conn:
        result = await conn.execute(
            """
            UPDATE conversations 
            SET chat_title = %s 
            WHERE thread_id = %s AND is_deleted = FALSE
            RETURNING id
            """,
            [body.chat_title, thread_id]
        )
        conversation = await result.fetchone()

        if conversation is None:
            return {"detail": "Conversation not found or has been deleted"}, status.HTTP_404_NOT_FOUND

    return {
        "message": "Chat title updated successfully",
        "thread_id": thread_id,
        "chat_title": body.chat_title
    }

@router.delete("/conversations/{thread_id}")
async def soft_delete_conversation(thread_id: str):
    """Soft delete a conversation by setting is_deleted to TRUE."""
    async with get_db() as conn:
        result = await conn.execute(
            """
            UPDATE conversations 
            SET is_deleted = TRUE 
            WHERE thread_id = %s AND is_deleted = FALSE
            RETURNING id
            """,
            [thread_id]
        )
        conversation = await result.fetchone()

        if conversation is None:
            return {"detail": "Conversation not found or already deleted"}, status.HTTP_404_NOT_FOUND

    return {
        "message": "Conversation soft deleted successfully",
        "thread_id": thread_id
    }

@router.get("/conversations/{thread_id}")
async def get_conversation_details(thread_id: str, request: Request):
    """Return metadata details for a single conversation thread."""
    async with get_db() as conn:
        row = await conn.execute(
            """
            SELECT thread_id, chat_title, created_at, is_deleted
            FROM conversations
            WHERE thread_id = %s
            """,
            [thread_id]
        )
        conversation = await row.fetchone()

        if conversation is None:
            return {"detail": "Conversation not found"} # Can also raise HTTPException(status_code=404)

    return {
        "thread_id": conversation[0],
        "chat_title": conversation[1],
        "created_at": str(conversation[2]),
        "is_deleted": conversation[3]
    }

@router.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """Receive a PDF, process it, and store embeddings in PGVector."""

    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed."
        )
    
    # Step 1: Read the uploaded file bytes
    content = await file.read()

    # Step 2: Save to a temp file (PyPDFLoader needs a real path)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        # Step 3: Process PDF → embed → store in PGVector
        process_pdf(tmp_path, filename=file.filename)
    finally:
        # Step 4: Always delete temp file, even if error occurs
        os.unlink(tmp_path)

    return {"message": "PDF processed successfully", "filename": file.filename}