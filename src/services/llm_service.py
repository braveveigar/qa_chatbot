import json
from openai import OpenAI
from src.config import CHAT_MODEL, EMBEDDING_MODEL
from src.prompts import (
    CLASSIFY_SYSTEM_PROMPT, GENERATE_SYSTEM_PROMPT,
    CLASSIFY_TOOLS, GENERATE_TOOLS,
)
from src.repositories import vector_repository

_client: OpenAI | None = None


class ClarificationRequested(Exception):
    def __init__(self, question: str):
        self.question = question


def init():
    global _client
    _client = OpenAI()


# ── Step 1: 카테고리 분류 ────────────────────────────────────────────────────

def _classify_category(question: str, chat_history: list) -> str:
    input_items = [
        {"role": "system", "content": CLASSIFY_SYSTEM_PROMPT},
        *[{"role": m["role"], "content": m["message"]} for m in chat_history],
        {"role": "user", "content": question},
    ]
    response = _client.responses.create(
        model=CHAT_MODEL,
        input=input_items,
        tools=CLASSIFY_TOOLS,
        tool_choice={"type": "function", "name": "load_workflow"},
    )
    for out in response.output:
        if out.type == "function_call" and out.name == "load_workflow":
            args = json.loads(out.arguments)
            return args.get("category", "기타")
    return "기타"


# ── Step 2: 워크플로우 로드 / QA 검색 ────────────────────────────────────────

def _load_workflow(category: str) -> str:
    path = f"workflows/{category}.md"
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return _load_workflow("기타")
    except Exception as e:
        return f"워크플로우 로드 실패: {e}"


def _execute_search(query: str) -> str:
    try:
        vector = _client.embeddings.create(input=query, model=EMBEDDING_MODEL).data[0].embedding
        results = vector_repository.search(vector, limit=2)
        if not results or not results[0]:
            return "관련 정보를 찾을 수 없습니다."
        answers = [hit.entity.get("answer", "") for hit in results[0] if hit.entity.get("answer")]
        return "\n\n".join(answers) if answers else "관련 정보를 찾을 수 없습니다."
    except Exception as e:
        return f"검색 중 오류가 발생했습니다: {e}"


# ── Step 3: 답변 생성 ────────────────────────────────────────────────────────

def _stream_answer(question: str, chat_history: list, workflow: str, qa: str):
    system = f"{GENERATE_SYSTEM_PROMPT}\n\n## 워크플로우\n{workflow}\n\n## 관련 FAQ\n{qa}"
    input_items = [
        {"role": "system", "content": system},
        *[{"role": m["role"], "content": m["message"]} for m in chat_history],
        {"role": "user", "content": question},
    ]
    with _client.responses.stream(
        model=CHAT_MODEL,
        input=input_items,
        tools=GENERATE_TOOLS,
        tool_choice="auto",
    ) as stream:
        for event in stream:
            if event.type == "response.output_text.delta":
                yield event.delta
            elif event.type == "response.output_item.done":
                if event.item.type == "function_call" and event.item.name == "ask_clarification":
                    args = json.loads(event.item.arguments)
                    yield args.get("question", "")
                    return


# ── 진입점 ───────────────────────────────────────────────────────────────────

def run_agent(question: str, chat_history: list):
    category = _classify_category(question, chat_history)
    workflow = _load_workflow(category)
    qa = _execute_search(question)
    yield from _stream_answer(question, chat_history, workflow, qa)
