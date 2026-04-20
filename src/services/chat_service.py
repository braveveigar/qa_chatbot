from src.repositories import session_repository, vector_repository
from src.services import llm_service
from src.utils import stream_text

def process_chat(question: str):
    session_repository.save("user", question)
    chat_history = session_repository.load(10)

    relevance = llm_service.check_relevance(question, chat_history)

    if relevance['status'] == 424:
        answer = "질문을 정확히 이해하지 못 했어요. 혹시 다시 구체적으로 질문해주실 수 있나요?"
        session_repository.save("assistant", answer)
        return stream_text(answer)

    if relevance['status'] == 503:
        answer = relevance['result']
        session_repository.save("assistant", answer)
        return stream_text(answer)

    if relevance['result'] == '없음':
        answer = "저는 스마트 스토어 FAQ를 위한 챗봇입니다. 스마트 스토어에 대한 질문을 부탁드립니다."
        session_repository.save("assistant", answer)
        return stream_text(answer)

    try:
        question_vector = llm_service.embed(question)
    except Exception as e:
        answer = f"OpenAI API 연결에 문제가 발생해 답변을 가져올 수 없습니다. 관리자에게 문의해주세요. 에러: {e}"
        session_repository.save("assistant", answer)
        return stream_text(answer)

    if not vector_repository.is_connected():
        answer = "DB 연결에 문제가 발생해 답변을 가져올 수 없습니다. 관리자에게 문의해주세요."
        session_repository.save("assistant", answer)
        return stream_text(answer)

    db_res = vector_repository.search(question_vector, limit=2)

    if not db_res or len(db_res[0]) == 0:
        answer = "비슷한 질문을 찾을 수 없습니다."
        session_repository.save("assistant", answer)
        return stream_text(answer)

    def token_stream():
        full_answer = ""
        for token in llm_service.generate_answer(question, db_res, chat_history):
            full_answer += token
            yield token
        session_repository.save("assistant", full_answer)

    return token_stream()
