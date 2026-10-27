"""FastAPI application entrypoint."""
import os
from app import api_service
from contextlib import asynccontextmanager
from psycopg.rows import dict_row

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from fastapi import FastAPI
from psycopg import AsyncConnection
from app.graphs import graph

# --- 2. Manage Database Connection Pool via FastAPI Lifespan ---
# db_pool = None
# checkpointer = None
# compiled_graph = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool, checkpointer, compiled_graph
    
    # Establish async connection to PostgreSQL
    # Crucial: Must use autocommit=True and dict_row for LangGraph checkpoint setup
    conn_string = os.getenv("DATABASE_URL")
    db_pool = await AsyncConnection.connect(conn_string, autocommit=True, row_factory=dict_row)
    
    # Initialize and set up the PostgreSQL checkpointer
    checkpointer = AsyncPostgresSaver(db_pool)
    await checkpointer.setup() # Automatically creates required LangGraph tables if they don't exist
    
    # Compile the graph globally once
    app.state.compiled_graph = graph.compile(checkpointer=checkpointer)
    
    yield
    # Clean up on shutdown
    await db_pool.close()

app = FastAPI(title="FastAPI Backend", debug=False, lifespan=lifespan)

app.include_router(api_service.router, prefix="/api/v1")

@app.get("/")
def home():
    return {"message": "Backend is running from main!"}