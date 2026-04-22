from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import conversations, messages, health
from app.db.database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="BOT GPT API",
    description="Conversational AI Backend for BOT Consulting",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(conversations.router, prefix="/api/v1/conversations", tags=["Conversations"])
app.include_router(messages.router, prefix="/api/v1/conversations", tags=["Messages"])
