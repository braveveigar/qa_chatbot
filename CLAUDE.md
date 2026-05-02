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
- `SERVER_API_KEY` — API key for `X-API-Key` header auth on `/chat` and `/session/reset`

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
├── core/
│   ├── config.py                    # 환경변수 로드 및 검증
│   ├── dependencies.py              # API Key 인증 (verify_api_key)
│   ├── middleware.py                # LoggingMiddleware + Request ID + basicConfig
│   └── rate_limit.py                # slowapi Limiter 인스턴스
├── models/
│   └── chat.py                      # ChatRequest, SessionResetRequest
├── controllers/
│   ├── chat_controller.py           # POST /chat  (rate limit: 20/min)
│   ├── session_controller.py        # POST /session/reset
│   └── health_controller.py         # GET /health  (인증 없음)
├── services/
│   ├── chat_service.py              # 대화 저장·로드 + 에이전트 위임 + 대화 로깅
│   ├── llm_service.py               # 3단계 파이프라인 (tool calling + streaming)
│   └── prompts.py                   # 시스템 프롬프트 + 도구 정의
├── repositories/
│   ├── session_repository.py        # Redis 대화 내역 CRUD (session_id 기반)
│   └── vector_repository.py         # Milvus 벡터 검색
├── main.py                          # FastAPI app 생성, 미들웨어·라우터 등록
├── chatbot.py                       # Gradio UI (UUID 세션 자동 생성)
├── mcp_server.py                    # MCP 서버 (Claude Code 도구 연동)
└── init_db.py                       # 벡터 DB 초기화 (1회성)

workflows/                           # 카테고리별 워크플로우 규칙 (마크다운)
├── 배송.md
├── 반품_교환.md
├── 결제_환불.md
├── 판매자_관리.md
├── 상품_등록.md
└── 기타.md
```

## Agent Flow — `POST /chat`

요청 바디: `{"session_id": "<uuid>", "question": "<질문>"}`

1. `chat_service` — `session_id`로 사용자 메시지 Redis 저장, 최근 10개 대화 로드
2. `llm_service.run_agent` 고정 3단계 파이프라인 실행
   - **Step 1** `_classify_category()` — LLM이 `load_workflow` 도구를 강제 호출(`tool_choice`)해 카테고리 분류
   - **Step 2** `_load_workflow(category)` + `_execute_search(question)` — 코드에서 직접 실행
   - **Step 3** `_stream_answer()` — workflow + QA를 system prompt에 주입 후 스트리밍 생성
3. 완성된 답변 Redis 저장 + 대화 로그 기록

`ask_clarification` 도구는 Step 3에서만 사용 가능 — LLM이 정보 부족 판단 시 질문을 yield하고 즉시 종료.

## Prompts (`src/services/prompts.py`)

- `CLASSIFY_SYSTEM_PROMPT` + `CLASSIFY_TOOLS` — 카테고리 분류 전용 (`load_workflow`만)
- `GENERATE_SYSTEM_PROMPT` + `GENERATE_TOOLS` — 답변 생성 전용 (`ask_clarification`만)

## Session Management

- 모든 요청은 `session_id`(UUID)를 포함해야 함
- Gradio: 페이지 로드 시 `uuid.uuid4()`로 자동 생성 (`gr.State`)
- MCP 서버: 프로세스 시작 시 고유 ID 생성 (`mcp_{8자리 hex}`)
- Redis 키 = `session_id` 값 그대로 사용

## Middleware & Security

| 구성요소 | 위치 | 역할 |
|----------|------|------|
| LoggingMiddleware | `core/middleware.py` | 요청별 Request ID 생성, 응답 시간·상태 로그, `X-Request-ID` 헤더 |
| CORSMiddleware | `main.py` | Gradio(7860)만 허용 |
| verify_api_key | `core/dependencies.py` | `X-API-Key` 헤더 검증 (`/chat`, `/session/reset`에 적용) |
| Rate Limiter | `core/rate_limit.py` | IP당 `/chat` 20회/분 (slowapi) |

## OpenAI Timeouts & Error Handling

| 단계 | 타임아웃 | 타임아웃/오류 시 동작 |
|------|---------|-------------------|
| 카테고리 분류 | 15초 | `"기타"` fallback |
| 임베딩 생성 | 10초 | `"관련 정보를 찾을 수 없습니다."` fallback |
| 스트리밍 답변 | 60초 | 사용자에게 재시도 안내 메시지 yield |

`APITimeoutError`, `APIError`, JSON 파싱 실패 모두 개별 포착 — 스트림 크래시 없이 graceful degradation.

## Health Check — `GET /health`

모든 의존성이 정상이면 HTTP **200**, 하나라도 문제가 있으면 HTTP **503** 반환 (로드밸런서 자동 제외).

```json
{
  "status": "ok | degraded",
  "redis": "ok | error",
  "milvus": "ok | error",
  "openai": "ok | error"
}
```

## MCP Server

Claude Code에서 챗봇을 직접 도구로 사용하는 인터페이스:

```bash
# 등록 (최초 1회)
claude mcp add qa-chatbot -s user -- /path/to/venv/bin/python /path/to/src/mcp_server.py

# 상태 확인
claude mcp list
```

도구 목록:
- `chat(question)` — 챗봇에 질문, 전체 답변 반환
- `reset_session()` — 대화 내역 초기화

FastAPI 서버 없이 서비스 레이어를 직접 호출하므로 Redis만 실행 중이면 동작.

## Milvus Collection Schema (`qa_vector.db`)

- `id` (int), `vector` (1536-dim float), `question` (str), `answer` (str)
- Embedding dimension is fixed at 1536 — changing `EMBEDDING_MODEL` requires rebuilding via `python -m src.init_db`

## Workflow 수정 방법

`workflows/*.md` 파일만 편집하면 코드 변경 없이 답변 규칙·구조가 바뀝니다.
각 파일은 분류 기준 / 핵심 정보 추출 / 답변 구조 / 답변 규칙 섹션으로 구성됩니다.
경로 순회 방지를 위해 카테고리명은 `_VALID_CATEGORIES` 화이트리스트로 검증됩니다.
