from pydantic import BaseModel

class ChatRequest(BaseModel):
    session_id: str
    question: str

class SessionResetRequest(BaseModel):
    session_id: str
