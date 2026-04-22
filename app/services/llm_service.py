import httpx
import logging
from typing import List, Dict, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


def build_context_window(messages: List[Dict], max_tokens: int = settings.MAX_CONTEXT_TOKENS) -> List[Dict]:
    """
    Sliding window: keep the most recent messages that fit within token budget.
    Rough estimate: 1 token ≈ 4 chars.
    Always keep the system prompt separate.
    """
    windowed = []
    token_budget = max_tokens

    for msg in reversed(messages):
        estimated_tokens = len(msg.get("content", "")) // 4 + 10
        if token_budget - estimated_tokens < 0:
            logger.info("Context window reached. Truncating older messages.")
            break
        windowed.insert(0, msg)
        token_budget -= estimated_tokens

    return windowed


async def call_llm(
    conversation_history: List[Dict],
    user_message: str,
    rag_context: Optional[str] = None,
) -> str:
    """
    Call Groq LLM API.
    - conversation_history: list of {role, content} dicts (past turns)
    - user_message: current user input
    - rag_context: optional retrieved document chunks for RAG mode
    """
    if not settings.GROQ_API_KEY:
        logger.warning("GROQ_API_KEY not set. Returning mock response.")
        return "Hello! I'm BOT GPT. (LLM API key not configured – this is a mock response.)"

    system_content = settings.SYSTEM_PROMPT
    if rag_context:
        system_content += (
            f"\n\nUse the following retrieved context to answer the user's question:\n\n"
            f"--- CONTEXT START ---\n{rag_context}\n--- CONTEXT END ---\n\n"
            "If the answer is not in the context, say so."
        )

    # Build messages for API
    api_messages = [{"role": "system", "content": system_content}]

    # Apply sliding window to history
    windowed_history = build_context_window(conversation_history)
    api_messages.extend(windowed_history)
    api_messages.append({"role": "user", "content": user_message})

    payload = {
        "model": settings.GROQ_MODEL,
        "messages": api_messages,
        "max_tokens": 1024,
        "temperature": 0.7,
    }

    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(settings.GROQ_API_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            reply = data["choices"][0]["message"]["content"]
            logger.info(
                "LLM call success | tokens_used=%s",
                data.get("usage", {}).get("total_tokens", "?"),
            )
            return reply

    except httpx.TimeoutException:
        logger.error("LLM API timeout")
        raise RuntimeError("LLM request timed out. Please try again.")
    except httpx.HTTPStatusError as e:
        logger.error("LLM API HTTP error: %s", e.response.text)
        raise RuntimeError(f"LLM API error: {e.response.status_code}")
    except Exception as e:
        logger.error("Unexpected LLM error: %s", str(e))
        raise RuntimeError("Unexpected error calling LLM.")
