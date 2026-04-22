import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = "llama3-8b-8192"
    GROQ_API_URL: str = "https://api.groq.com/openai/v1/chat/completions"

    # Context management
    MAX_CONTEXT_TOKENS: int = 6000      # leave room under 8192 limit
    MAX_HISTORY_MESSAGES: int = 20      # sliding window
    SYSTEM_PROMPT: str = (
        "You are BOT GPT, a helpful AI assistant built by BOT Consulting. "
        "Be concise, accurate, and professional."
    )

    # DB
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./botgpt.db")

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
