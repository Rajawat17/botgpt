# BOT GPT – Conversational AI Backend

A production-grade conversational AI backend built with **FastAPI + SQLite/PostgreSQL + Groq (Llama 3)**.

---

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| API Framework | FastAPI | Async-native, auto Swagger docs, Pydantic validation |
| Database | SQLite (dev) / PostgreSQL (prod) | SQLite for zero-setup local dev; swap to Postgres via env var |
| ORM | SQLAlchemy 2.0 | Declarative models, easy migrations |
| LLM Provider | Groq API (Llama 3) | Free tier, fast inference, OpenAI-compatible API |
| HTTP Client | httpx | Async HTTP calls to LLM |
| Containerisation | Docker + Compose | One-command local run |
| CI/CD | GitHub Actions | Lint → Test → Docker build on every push |

---

## Project Structure

```
botgpt/
├── app/
│   ├── main.py                  # FastAPI app, middleware, router registration
│   ├── api/routes/
│   │   ├── conversations.py     # CRUD: create, list, get, delete
│   │   ├── messages.py          # POST /{id}/messages – continue conversation
│   │   └── health.py            # GET /health/
│   ├── core/
│   │   └── config.py            # Settings via pydantic-settings + .env
│   ├── db/
│   │   └── database.py          # SQLAlchemy engine, session, get_db dependency
│   ├── models/
│   │   ├── models.py            # ORM models: User, Conversation, Message
│   │   └── schemas.py           # Pydantic request/response schemas
│   └── services/
│       ├── llm_service.py       # Groq API call + sliding-window context builder
│       └── conversation_service.py  # Business logic for all conversation ops
├── tests/
│   └── test_api.py              # 9 unit tests (pytest + TestClient)
├── .github/workflows/
│   └── ci.yml                   # GitHub Actions: lint → test → docker build
├── Dockerfile                   # Multi-stage build (builder + runtime)
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

---

## Quick Start

### 1. Clone & configure

```bash
git clone https://github.com/YOUR_USERNAME/botgpt.git
cd botgpt
cp .env.example .env
# Edit .env and add your GROQ_API_KEY (free at https://console.groq.com)
```

### 2. Run locally (Python)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API available at **http://localhost:8000**  
Swagger docs at **http://localhost:8000/docs**

### 3. Run with Docker

```bash
docker compose up --build
```

---

## API Reference

### Health
```
GET /health/
→ { "status": "ok", "service": "BOT GPT API" }
```

### Conversations

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/conversations/` | Start new conversation (first message + LLM reply) |
| `GET` | `/api/v1/conversations/?user_id=X` | List all conversations (paginated) |
| `GET` | `/api/v1/conversations/{id}` | Get full conversation with message history |
| `POST` | `/api/v1/conversations/{id}/messages` | Add a message, get LLM reply |
| `DELETE` | `/api/v1/conversations/{id}` | Delete conversation and all messages |

### Example: Start a conversation

```bash
curl -X POST http://localhost:8000/api/v1/conversations/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-123",
    "first_message": "Explain recursion in Python",
    "mode": "open"
  }'
```

### Example: Continue conversation

```bash
curl -X POST http://localhost:8000/api/v1/conversations/{conversation_id}/messages \
  -H "Content-Type: application/json" \
  -d '{ "user_message": "Give me a code example" }'
```

### Example: List conversations (paginated)

```bash
curl "http://localhost:8000/api/v1/conversations/?user_id=user-123&page=1&page_size=10"
```

---

## Data Schema

```
User          ──< Conversation ──< Message
id (PK)           id (PK)            id (PK)
email             user_id (FK)       conversation_id (FK)
name              title              role  (user|assistant|system)
created_at        mode               content
                  is_active          token_count
                  total_tokens       created_at
                  created_at
                  updated_at
```

---

## LLM Context & Cost Management

- **Sliding window** – only recent messages within `MAX_CONTEXT_TOKENS` (default 6 000) are sent to the LLM, preventing token overflow.
- **Token estimation** – rough `len(content) // 4` estimate; easy to swap for `tiktoken` for precision.
- **System prompt** – single, compact system prompt prepended to every request.
- **RAG mode** – retrieved document chunks injected into the system prompt instead of raw document content, keeping token count lean.

---

## RAG Architecture (Design)

```
User message
     │
     ▼
[Embedding / keyword search over document chunks]
     │
     ▼
Top-K relevant chunks retrieved
     │
     ▼
LLM call:
  system  = base prompt + retrieved chunks
  history = sliding window of past turns
  user    = current message
```

For the prototype, RAG is simulated with hardcoded/in-memory chunks. In production, swap the retrieval step for **pgvector** (Postgres) or **Chroma/Qdrant**.

---

## Running Tests

```bash
pytest tests/ -v
```

9 tests covering: health check, create conversation, list, get detail, add message, 404 handling, delete, context window logic, and pagination.

---

## CI/CD Pipeline

`.github/workflows/ci.yml` runs on every push to `main` / `develop`:

1. **Lint** – flake8 with 120 char line limit
2. **Unit tests** – pytest against in-memory SQLite, LLM mocked
3. **Docker build** – confirms image builds cleanly (no push unless deploy step uncommented)

To enable deployment, uncomment the `deploy` job and add your cloud provider secrets (e.g. `FLY_API_TOKEN`).

---

## Error Handling

| Scenario | HTTP Code | Behaviour |
|---|---|---|
| Conversation not found | 404 | `{ "detail": "Conversation not found" }` |
| LLM timeout | 502 | `{ "detail": "LLM request timed out. Please try again." }` |
| LLM API error | 502 | `{ "detail": "LLM API error: <status>" }` |
| Validation error | 422 | Pydantic auto-generated field errors |

---

## Scalability Notes

| Bottleneck at 1M users | Strategy |
|---|---|
| API layer | Horizontal scaling behind a load balancer (e.g. AWS ALB) |
| Database | Migrate to PostgreSQL + read replicas; shard by `user_id` |
| LLM calls | Async task queue (Celery + Redis) for non-blocking replies |
| Context rebuild | Cache recent history in Redis (TTL = session length) |
