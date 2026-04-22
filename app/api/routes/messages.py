from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.schemas import MessageCreate, ConversationDetail
from app.services import conversation_service

router = APIRouter()


@router.post("/{conversation_id}/messages", response_model=ConversationDetail)
async def add_message(
    conversation_id: str,
    payload: MessageCreate,
    db: Session = Depends(get_db),
):
    """Add a new user message to an existing conversation and get the LLM reply."""
    try:
        conv = await conversation_service.add_message(db, conversation_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return conv
