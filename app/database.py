"""
database.py

Provides a simple async PostgreSQL connection helper using psycopg3.
No SQLAlchemy ORM — all queries are written as raw SQL.

Usage (inside a FastAPI route):
    async with get_db() as conn:
        await conn.execute("SELECT * FROM users;")
"""
import os
from contextlib import asynccontextmanager

import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


@asynccontextmanager
async def get_db():
    """Async context manager that yields a psycopg3 connection.
    
    Automatically commits on success, rolls back on error, and closes the connection.
    
    Example:
        async with get_db() as conn:
            await conn.execute("INSERT INTO users (name) VALUES (%s)", ["Alice"])
    """
    conn = await psycopg.AsyncConnection.connect(DATABASE_URL)
    try:
        yield conn
        await conn.commit()
    except Exception:
        await conn.rollback()
        raise
    finally:
        await conn.close()
