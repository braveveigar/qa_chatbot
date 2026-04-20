import json
from openai import OpenAI
from src.config import CHAT_MODEL, EMBEDDING_MODEL
from src.prompts import SYSTEM_PROMPT, TOOLS
from src.repositories import vector_repository

_client: OpenAI | None = None
_MAX_TOOL_ITERATIONS = 5

def init():
    global _client
    _client = OpenAI()

# ── 도구 실행 ─────────────────────────────────────────────────────────────────

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

def _execute_tool(name: str, arguments: str, question: str) -> str:
    args = json.loads(arguments)
    if name == "load_workflow":
        return _load_workflow(args.get("category", "기타"))
    if name == "search_qa":
        return _execute_search(args.get("query", question))
    return "알 수 없는 도구입니다."

def _to_input_items(response):
    items = []

    for out in response.output:
        # 모델이 말한 텍스트
        if out.type == "output_text":
            items.append({
                "role": "assistant",
                "content": out.text,
            })

        # 모델이 호출한 tool
        elif out.type == "function_call":
            items.append({
                "type": "function_call",
                "name": out.name,
                "call_id": out.call_id,
                "arguments": out.arguments,
            })

    return items

# ── 에이전트 루프 ──────────────────────────────────────────────────────────────

def run_agent(question: str, chat_history: list):
    # chat_history는 {"role": ..., "message": ...} 형식 → "content" 키로 변환
    input_items = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *[{"role": m["role"], "content": m["message"]} for m in chat_history],
        {"role": "user", "content": question},
    ]

    for _ in range(_MAX_TOOL_ITERATIONS):
        tool_calls = []

        with _client.responses.stream(
            model=CHAT_MODEL,
            input=input_items,
            tools=TOOLS,
        ) as stream:
            for event in stream:
                if event.type == "response.output_text.delta":
                    yield event.delta
                elif event.type == "response.output_item.done":
                    if event.item.type == "function_call":
                        tool_calls.append(event.item)

            response = stream.get_final_response()

        # 컨텍스트 누적: 교체 대신 extend
        input_items = input_items + _to_input_items(response)

        if not tool_calls:
            break

        for call in tool_calls:
            input_items.append({
                "type": "function_call_output",
                "call_id": call.call_id,
                "output": _execute_tool(call.name, call.arguments, question),
            })
