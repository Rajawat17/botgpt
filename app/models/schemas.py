from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# ---------- User ----------
class UserCreate(BaseModel):
    email: str
    name: str


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Message ----------
class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    token_count: int
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Conversation ----------
class ConversationCreate(BaseModel):
    user_id: str
    first_message: str
    mode: Optional[str] = "open"        # "open" | "rag"
    title: Optional[str] = None


class ConversationOut(BaseModel):
    id: str
    user_id: str
    title: Optional[str]
    mode: str
    is_active: bool
    total_tokens: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationDetail(ConversationOut):
    messages: List[MessageOut] = []


class MessageCreate(BaseModel):
    user_message: str


class PaginatedConversations(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[ConversationOut]
