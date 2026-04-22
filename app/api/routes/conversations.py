from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.schemas import (
    ConversationCreate, ConversationOut, ConversationDetail, PaginatedConversations
)
from app.services import conversation_service

router = APIRouter()


@router.post("/", response_model=ConversationDetail, status_code=201)
async def create_conversation(
    payload: ConversationCreate,
    db: Session = Depends(get_db),
):
    """Start a new conversation with the first user message."""
    conv = await conversation_service.create_conversation(db, payload)
    return conv


@router.get("/", response_model=PaginatedConversations)
def list_conversations(
    user_id: str = Query(..., description="User ID to filter by"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List all conversations for a user (paginated)."""
    total, items = conversation_service.list_conversations(db, user_id, page, page_size)
    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: str, db: Session = Depends(get_db)):
    """Get full conversation history by ID."""
    conv = conversation_service.get_conversation(db, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: str, db: Session = Depends(get_db)):
    """Delete a conversation and all its messages."""
    deleted = conversation_service.delete_conversation(db, conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
