# 네이버 스마트스토어 QA 챗봇

네이버 스마트스토어 FAQ 데이터(2,717개)를 벡터 DB에 저장하고, 질문이 들어오면 유사한 QA를 검색(RAG)하여 GPT로 구조화된 답변을 생성하는 챗봇입니다.

![실제 채팅 예시](./data/chat_example.png)

---

## 기술 스택

- **언어 및 프레임워크**: Python 3.10+, FastAPI, Gradio
- **데이터베이스**: Redis (대화 내역), Milvus Lite (벡터 검색)
- **AI**: OpenAI Embeddings, GPT-4o mini
- **인프라**: Shell Script 실행 자동화

---

## 프로젝트 구조

```
src/
├── config.py                  # 환경변수 로드
├── main.py                    # FastAPI 앱 생성 및 라우터 등록
├── chatbot.py                 # Gradio UI
├── init_db.py                 # 벡터 DB 초기화 (1회성)
├── utils.py                   # 공통 유틸리티
├── models/
│   └── chat.py                # Pydantic 요청 스키마
├── controllers/
│   ├── chat_controller.py     # POST /chat
│   ├── session_controller.py  # POST /session/reset
│   └── health_controller.py   # GET /health
├── services/
│   ├── chat_service.py        # 대화 저장·로드 + 에이전트 위임
│   └── llm_service.py         # 에이전트 루프 (tool calling + streaming)
└── repositories/
    ├── session_repository.py  # Redis 대화 내역 CRUD
    └── vector_repository.py   # Milvus 벡터 검색

workflows/                     # 카테고리별 워크플로우 규칙 (마크다운)
├── 배송.md
├── 반품_교환.md
├── 결제_환불.md
├── 판매자_관리.md
├── 상품_등록.md
└── 기타.md
```

답변 규칙을 바꾸고 싶다면 **`workflows/*.md` 파일만 편집**하면 됩니다. 코드 변경 없이 답변 구조·정책이 반영됩니다.

---

## 실행 전 준비

**1. Redis 설치**

```bash
# macOS
brew install redis

# Ubuntu
sudo apt-get install redis-server
```

**2. 환경 변수 설정**

`.env.template`을 `.env`로 복사 후 값 입력:

| 변수 | 설명 |
|------|------|
| `OPENAI_API_KEY` | OpenAI API 키 (필수) |
| `EMBEDDING_MODEL` | 임베딩 모델 (예: `text-embedding-3-small`) |
| `CHAT_MODEL` | 채팅 모델 (예: `gpt-4o-mini`) |
| `COLLECTION_NAME` | Milvus 컬렉션 이름 (예: `qa_collection`) |

> `EMBEDDING_MODEL`을 변경하면 벡터 DB를 반드시 재빌드해야 합니다.

---

## 실행 방법

```bash
# 최초 1회: 환경 세팅
./setup.sh

# 이후 실행
./run.sh
```

- FastAPI: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- Gradio UI: [http://127.0.0.1:7860](http://127.0.0.1:7860)

**개별 실행 (venv 활성화 후, 프로젝트 루트에서):**

```bash
redis-server --daemonize yes
uvicorn src.main:app &
python -m src.chatbot
```

> 모든 명령은 프로젝트 루트에서 실행해야 합니다 (`src.*` 절대 임포트 사용).

---

## 벡터 DB 재빌드

`qa_vector.db`가 없거나 손상된 경우:

```bash
python -m src.init_db
```

이미 `qa_vector.db`가 포함되어 있으므로 일반적으로 불필요합니다.

---

## 테스트

```bash
venv/bin/pytest tests/ -v
```
