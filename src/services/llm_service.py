import json
import logging
from openai import OpenAI, APITimeoutError, APIError
from src.core.config import CHAT_MODEL, EMBEDDING_MODEL
from src.services.prompts import (
    CLASSIFY_SYSTEM_PROMPT, GENERATE_SYSTEM_PROMPT,
    CLASSIFY_TOOLS, GENERATE_TOOLS,
)
from src.repositories import vector_repository

logger = logging.getLogger(__name__)

_client: OpenAI | None = None

_TIMEOUT_CLASSIFY = 15.0
_TIMEOUT_EMBED    = 10.0
_TIMEOUT_STREAM   = 60.0


class ClarificationRequested(Exception):
    def __init__(self, question: str):
        self.question = question


def init():
    global _client
    _client = OpenAI()

def is_ready() -> bool:
    return _client is not None


# ── Step 1: 카테고리 분류 ────────────────────────────────────────────────────

def _classify_category(question: str, chat_history: list) -> str:
    input_items = [
        {"role": "system", "content": CLASSIFY_SYSTEM_PROMPT},
        *[{"role": m["role"], "content": m["message"]} for m in chat_history],
        {"role": "user", "content": question},
    ]
    try:
        response = _client.responses.create(
            model=CHAT_MODEL,
            input=input_items,
            tools=CLASSIFY_TOOLS,
            tool_choice={"type": "function", "name": "load_workflow"},
            timeout=_TIMEOUT_CLASSIFY,
        )
        for out in response.output:
            if out.type == "function_call" and out.name == "load_workflow":
                try:
                    args = json.loads(out.arguments)
                except json.JSONDecodeError:
                    logger.warning("카테고리 분류 JSON 파싱 실패")
                    return "기타"
                return args.get("category", "기타")
    except APITimeoutError:
        logger.warning("카테고리 분류 타임아웃 (%.0fs 초과)", _TIMEOUT_CLASSIFY)
    except APIError as e:
        logger.error("카테고리 분류 API 오류: %s", e)
    return "기타"


# ── Step 2: 워크플로우 로드 / QA 검색 ────────────────────────────────────────

_VALID_CATEGORIES = {"배송", "반품_교환", "결제_환불", "판매자_관리", "상품_등록", "기타"}

def _load_workflow(category: str) -> str:
    if category not in _VALID_CATEGORIES:
        category = "기타"
    path = f"workflows/{category}.md"
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        if category == "기타":
            return ""
        return _load_workflow("기타")
    except Exception as e:
        return f"워크플로우 로드 실패: {e}"


def _execute_search(query: str) -> str:
    try:
        vector = _client.embeddings.create(
            input=query, model=EMBEDDING_MODEL, timeout=_TIMEOUT_EMBED
        ).data[0].embedding
        results = vector_repository.search(vector, limit=2)
        if not results or not results[0]:
            return "관련 정보를 찾을 수 없습니다."
        answers = [hit.entity.get("answer", "") for hit in results[0] if hit.entity.get("answer")]
        return "\n\n".join(answers) if answers else "관련 정보를 찾을 수 없습니다."
    except APITimeoutError:
        logger.warning("임베딩 타임아웃 (%.0fs 초과)", _TIMEOUT_EMBED)
        return "관련 정보를 찾을 수 없습니다."
    except Exception as e:
        logger.warning("벡터 검색 실패: %s", e)
        return "관련 정보를 찾을 수 없습니다."


# ── Step 3: 답변 생성 ────────────────────────────────────────────────────────

def _stream_answer(question: str, chat_history: list, workflow: str, qa: str):
    system = f"{GENERATE_SYSTEM_PROMPT}\n\n## 워크플로우\n{workflow}\n\n## 관련 FAQ\n{qa}"
    input_items = [
        {"role": "system", "content": system},
        *[{"role": m["role"], "content": m["message"]} for m in chat_history],
        {"role": "user", "content": question},
    ]
    try:
        with _client.responses.stream(
            model=CHAT_MODEL,
            input=input_items,
            tools=GENERATE_TOOLS,
            tool_choice="auto",
            timeout=_TIMEOUT_STREAM,
        ) as stream:
            for event in stream:
                if event.type == "response.output_text.delta":
                    yield event.delta
                elif event.type == "response.output_item.done":
                    if event.item.type == "function_call" and event.item.name == "ask_clarification":
                        try:
                            args = json.loads(event.item.arguments)
                        except json.JSONDecodeError:
                            logger.warning("ask_clarification JSON 파싱 실패")
                            return
                        yield args.get("question", "")
                        return
    except APITimeoutError:
        logger.error("답변 생성 타임아웃 (%.0fs 초과)", _TIMEOUT_STREAM)
        yield "\n\n[응답 시간이 초과되었습니다. 다시 시도해주세요.]"
    except APIError as e:
        logger.error("답변 생성 API 오류: %s", e)
        yield "\n\n[오류가 발생했습니다. 다시 시도해주세요.]"


# ── 진입점 ───────────────────────────────────────────────────────────────────

def run_agent(question: str, chat_history: list):
    category = _classify_category(question, chat_history)
    logger.info("질문 분류: %s | 질문: %.50s", category, question)
    workflow = _load_workflow(category)
    qa = _execute_search(question)
    yield from _stream_answer(question, chat_history, workflow, qa)
