# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Project

```bash
# Full startup (venv setup → pip install → Redis → FastAPI → Gradio)
./run.sh

# Run components individually (after activating venv, from project root)
source venv/bin/activate
redis-server --daemonize yes
uvicorn src.server:app &        # FastAPI on port 8000
python -m src.chatbot           # Gradio UI on port 7860

# Rebuild the vector DB from scratch (only if qa_vector.db is missing/corrupt)
python -m src.init_db
```

> **중요**: `src.*` 절대 임포트를 사용하므로 모든 명령은 프로젝트 루트에서 실행해야 합니다.

## Environment Setup

Copy `.env.template` to `.env` and set:
- `OPENAI_API_KEY` — required for both embeddings and chat
- `EMBEDDING_MODEL` — e.g. `text-embedding-3-small` (must match what was used to build `qa_vector.db`)
- `CHAT_MODEL` — e.g. `gpt-4o-mini`
- `COLLECTION_NAME` — Milvus collection name, e.g. `qa_collection`
- `SERVER_API_KEY` — defined but currently unused in server logic

## Architecture

**Three-process system** — all must run simultaneously:

| Process | File | Port |
|---------|------|------|
| Vector search + LLM API | `src/server.py` | 8000 |
| Chat UI | `src/chatbot.py` | 7860 |
| Session store | Redis | 6379 |

**Layer structure (Controller → Service → Repository):**

```
src/
├── config.py                        # 환경변수 로드
├── server.py                        # FastAPI app 생성, 라우터 등록
├── chatbot.py                       # Gradio UI
├── init_db.py                       # 벡터 DB 초기화 (1회성)
├── models/
│   └── chat.py                      # Pydantic 요청 스키마
├── controllers/
│   └── chat_controller.py           # HTTP 요청/응답만 담당 (APIRouter)
├── services/
│   ├── chat_service.py              # 비즈니스 로직 오케스트레이션
│   └── llm_service.py              # OpenAI 호출 (관련성 판단, 임베딩, 답변 생성)
└── repositories/
    ├── session_repository.py        # Redis 대화 내역 CRUD
    └── vector_repository.py         # Milvus 벡터 검색
```

**Request flow — `POST /chat`:**
1. `chat_controller` → `chat_service.process_chat(question)`
2. `session_repository.save` → `session_repository.load(10)` (최근 10개)
3. `llm_service.check_relevance` — 스마트스토어 무관 질문 조기 차단
4. `llm_service.embed` → `vector_repository.search(limit=2)` — RAG
5. `llm_service.generate_answer` — 스트리밍 토큰 yield
6. 완성된 답변 `session_repository.save`

**Milvus collection schema** (`qa_vector.db`):
- `id` (int), `vector` (1536-dim float), `question` (str), `answer` (str)
- Embedding dimension is fixed at 1536 — changing `EMBEDDING_MODEL` requires rebuilding via `python -m src.init_db`

**Known limitations:**
- `chat_id` is hardcoded as `'naver_qa_test'` in `session_repository.py` — no multi-session support
- `SERVER_API_KEY` is loaded in `config.py` but never validated in any endpoint
- Relevance classification uses a full LLM call; could be replaced with a lightweight classifier
