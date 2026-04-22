import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.models import Conversation, Message, User
from app.models.schemas import ConversationCreate, MessageCreate
from app.services.llm_service import call_llm

logger = logging.getLogger(__name__)


# ── helpers ──────────────────────────────────────────────────────────────────

def _get_or_create_user(db: Session, user_id: str) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        user = User(id=user_id, email=f"{user_id}@botgpt.local", name="Default User")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def _history_dicts(messages: List[Message]) -> List[dict]:
    return [{"role": m.role, "content": m.content} for m in messages]


# ── CRUD ──────────────────────────────────────────────────────────────────────

def list_conversations(db: Session, user_id: str, page: int = 1, page_size: int = 20):
    q = db.query(Conversation).filter(
        Conversation.user_id == user_id,
        Conversation.is_active == True,
    ).order_by(Conversation.updated_at.desc())
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return total, items


def get_conversation(db: Session, conversation_id: str) -> Optional[Conversation]:
    return db.query(Conversation).filter(Conversation.id == conversation_id).first()


def delete_conversation(db: Session, conversation_id: str) -> bool:
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        return False
    db.delete(conv)
    db.commit()
    return True


async def create_conversation(db: Session, payload: ConversationCreate) -> Conversation:
    _get_or_create_user(db, payload.user_id)

    # Auto-title from first message
    title = payload.title or (payload.first_message[:60] + "…" if len(payload.first_message) > 60 else payload.first_message)

    conv = Conversation(
        user_id=payload.user_id,
        title=title,
        mode=payload.mode or "open",
    )
    db.add(conv)
    db.flush()

    # Save the user message
    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content=payload.first_message,
        token_count=len(payload.first_message) // 4,
    )
    db.add(user_msg)
    db.flush()

    # Call LLM
    try:
        reply = await call_llm([], payload.first_message)
    except RuntimeError as e:
        reply = f"[Error: {str(e)}]"

    # Save assistant message
    assistant_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=reply,
        token_count=len(reply) // 4,
    )
    db.add(assistant_msg)
    conv.total_tokens += user_msg.token_count + assistant_msg.token_count

    db.commit()
    db.refresh(conv)
    logger.info("Created conversation id=%s", conv.id)
    return conv


async def add_message(db: Session, conversation_id: str, payload: MessageCreate) -> Conversation:
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise ValueError(f"Conversation {conversation_id} not found")

    # Persist user turn
    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content=payload.user_message,
        token_count=len(payload.user_message) // 4,
    )
    db.add(user_msg)
    db.flush()

    # Build history (excluding just-saved user msg so we pass it explicitly)
    history = _history_dicts(conv.messages[:-1])   # all but the new one

    # Call LLM
    try:
        reply = await call_llm(history, payload.user_message)
    except RuntimeError as e:
        reply = f"[Error: {str(e)}]"

    # Persist assistant turn
    assistant_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=reply,
        token_count=len(reply) // 4,
    )
    db.add(assistant_msg)
    conv.total_tokens += user_msg.token_count + assistant_msg.token_count

    db.commit()
    db.refresh(conv)
    return conv
