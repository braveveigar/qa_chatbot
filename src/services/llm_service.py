from openai import OpenAI
from src.config import CHAT_MODEL, EMBEDDING_MODEL

_client: OpenAI | None = None

def init():
    global _client
    _client = OpenAI()

def check_relevance(question: str, chat_history: list) -> dict:
    try:
        response = _client.responses.create(
            model=CHAT_MODEL,
            input=f'''
사용자와 챗봇 사이의 대화 내역을 보고, 현재 질문이 스마트 스토어와 관련 있는지 판단해주세요.
- 이전 대화 내용과 현재 질문을 모두 고려해야 합니다.
- 관련 있으면 "있음", 관련 없으면 "없음"만 출력하세요.

대화 내역:
{chat_history}

현재 질문:
{question}
'''
        )
        result = response.output_text
        if result not in ['없음', '있음']:
            return {"status": 424, "result": f"관련 여부 분류 실패: {result}"}
        return {"status": 200, "result": result}
    except Exception as e:
        return {"status": 503, "result": f"OpenAI API 연결을 실패 했어요. 에러 내역: {e}"}

def embed(text: str) -> list:
    response = _client.embeddings.create(input=text, model=EMBEDDING_MODEL)
    return response.data[0].embedding

def generate_answer(question: str, db_res, chat_history: list):
    answers_text = ""
    for hit in db_res[0]:
        ans = hit.entity.get("answer")
        if ans:
            answers_text += f"답변 예시: {ans}\n"

    with _client.responses.stream(
        model=CHAT_MODEL,
        input=f"""
당신은 스마트 스토어 전문 답변가입니다.
아래는 이전 대화 내용입니다. 이전 대화를 기억하고, 현재 질문에 이어서 자연스럽게 답변하세요.
아래 제공된 내용은 사용자가 궁금해 하는 질문과 관련된 실제 정보입니다. 이 내용을 기반으로 답변하되, 친절하고 간략하게 작성해주세요.
답변 끝에는 사용자가 추가로 물어볼 법한 질문도 자연스럽게 포함해주세요.

이전 대화:
{chat_history}

현재 질문:
{question}

참고 내용 (RAG로 찾아온 답변):
{answers_text}
"""
    ) as stream:
        for event in stream:
            if event.type == "response.output_text.delta":
                yield event.delta
