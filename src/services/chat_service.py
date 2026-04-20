from src.repositories import session_repository
from src.services import llm_service

def process_chat(question: str):
    session_repository.save("user", question)
    chat_history = session_repository.load(10)

    def token_stream():
        full_answer = ""
        for token in llm_service.run_agent(question, chat_history):
            full_answer += token
            yield token
        session_repository.save("assistant", full_answer)

    return token_stream()
