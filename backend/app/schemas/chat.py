"""Pydantic schemas for chat-related API models."""

from typing import List, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request to send a chat message."""
    query: str = Field(..., description="User's question")
    wmoId: str = Field(..., description="WMO ID of the active float")
    cycle: int = Field(..., description="Active cycle number")


class ChatResponse(BaseModel):
    """Response from the chat endpoint."""
    text: str
    citations: List[str]
    verified: bool
    forecast_context: Optional[dict] = None