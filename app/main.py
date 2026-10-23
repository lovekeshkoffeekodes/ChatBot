"""FastAPI application entrypoint."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

from app.api.v1 import jobs

app = FastAPI(title="FastAPI Backend", debug=False)

app.include_router(jobs.router, prefix="/api/v1")

@app.get("/")
def home():
    return {"message": "Backend is running from main!"}