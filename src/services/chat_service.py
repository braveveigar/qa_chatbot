import logging
from src.repositories import session_repository
from src.services import llm_service

logger = logging.getLogger(__name__)

def process_chat(session_id: str, question: str):
    session_repository.save(session_id, "user", question)
    chat_history = session_repository.load(session_id, 10)

    def token_stream():
        full_answer = ""
        for token in llm_service.run_agent(question, chat_history):
            full_answer += token
            yield token
        session_repository.save(session_id, "assistant", full_answer)
        logger.info(
            "대화 완료 | session=%s | 질문=%.80s | 답변=%.120s",
            session_id, question, full_answer,
        )

    return token_stream()
