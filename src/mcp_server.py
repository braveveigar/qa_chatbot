import sys, os
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(_root)
if _root not in sys.path:
    sys.path.insert(0, _root)

import uuid
from mcp.server.fastmcp import FastMCP
from src.repositories import vector_repository, session_repository
from src.services import llm_service, chat_service

vector_repository.init()
llm_service.init()
session_repository.init()

mcp = FastMCP("스마트스토어 QA 챗봇")
_SESSION_ID = f"mcp_{uuid.uuid4().hex[:8]}"


@mcp.tool()
def chat(question: str) -> str:
    """네이버 스마트스토어 FAQ 챗봇에 질문합니다. 배송, 반품/교환, 결제/환불 등 질문 가능."""
    return "".join(chat_service.process_chat(_SESSION_ID, question))


@mcp.tool()
def reset_session() -> str:
    """대화 내역을 초기화합니다."""
    session_repository.clear(_SESSION_ID)
    return "세션이 초기화되었습니다."


if __name__ == "__main__":
    mcp.run()
