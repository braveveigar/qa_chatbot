# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Project

```bash
# 최초 1회: 환경 세팅 (venv 생성 → pip install)
./setup.sh

# 매 실행: Redis → FastAPI → Gradio
./run.sh

# 개별 실행 (프로젝트 루트에서)
source venv/bin/activate
redis-server --daemonize yes
uvicorn src.main:app &          # FastAPI on port 8000
python -m src.chatbot           # Gradio UI on port 7860

# 벡터 DB 재빌드 (qa_vector.db 없거나 손상 시)
python -m src.init_db

# 테스트
venv/bin/pytest tests/ -v
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
| Vector search + LLM API | `src/main.py` | 8000 |
| Chat UI | `src/chatbot.py` | 7860 |
| Session store | Redis | 6379 |

**Layer structure (Controller → Service → Repository):**

```
src/
├── config.py                        # 환경변수 로드 및 검증
├── prompts.py                       # 시스템 프롬프트 + 도구 정의
├── main.py                          # FastAPI app 생성, 라우터 등록
├── chatbot.py                       # Gradio UI
├── init_db.py                       # 벡터 DB 초기화 (1회성)
├── utils.py                         # stream_text 유틸
├── models/
│   └── chat.py                      # Pydantic 요청 스키마
├── controllers/
│   ├── chat_controller.py           # POST /chat
│   ├── session_controller.py        # POST /session/reset
│   └── health_controller.py         # GET /health
├── services/
│   ├── chat_service.py              # 대화 저장·로드 + 에이전트 위임
│   └── llm_service.py               # 에이전트 루프 (tool calling + streaming)
└── repositories/
    ├── session_repository.py        # Redis 대화 내역 CRUD
    └── vector_repository.py         # Milvus 벡터 검색

workflows/                           # 카테고리별 워크플로우 규칙 (마크다운)
├── 배송.md
├── 반품_교환.md
├── 결제_환불.md
├── 판매자_관리.md
├── 상품_등록.md
└── 기타.md
```

**Agent flow — `POST /chat`:**
1. `chat_service` — 사용자 메시지 Redis 저장, 최근 10개 대화 로드
2. `llm_service.run_agent` 고정 3단계 파이프라인 실행
   - **Step 1** `_classify_category()` — LLM이 `load_workflow` 도구를 강제 호출(`tool_choice`)해 카테고리 분류
   - **Step 2** `_load_workflow(category)` + `_execute_search(question)` — 코드에서 직접 실행
   - **Step 3** `_stream_answer()` — workflow + QA를 system prompt에 주입 후 스트리밍 생성
3. 완성된 답변 Redis 저장

`ask_clarification` 도구는 Step 3에서만 사용 가능 — LLM이 정보 부족 판단 시 질문을 yield하고 즉시 종료.

**프롬프트 구조 (`src/prompts.py`):**
- `CLASSIFY_SYSTEM_PROMPT` + `CLASSIFY_TOOLS` — 카테고리 분류 전용 (load_workflow만)
- `GENERATE_SYSTEM_PROMPT` + `GENERATE_TOOLS` — 답변 생성 전용 (ask_clarification만)

**워크플로우 수정 방법:**
`workflows/*.md` 파일만 편집하면 코드 변경 없이 답변 규칙·구조가 바뀝니다.
각 파일은 분류 기준 / 핵심 정보 추출 / 답변 구조 / 답변 규칙 섹션으로 구성됩니다.

**Milvus collection schema** (`qa_vector.db`):
- `id` (int), `vector` (1536-dim float), `question` (str), `answer` (str)
- Embedding dimension is fixed at 1536 — changing `EMBEDDING_MODEL` requires rebuilding via `python -m src.init_db`

**Known limitations:**
- `chat_id` is hardcoded as `'naver_qa_test'` in `session_repository.py` — no multi-session support
