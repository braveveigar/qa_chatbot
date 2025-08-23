'''
FastAPI 기반 서버 모듈입니다.
- 대화 내용을 API로 LLM과 상호 작용해 답변 도출 (답변은 스트리밍으로 받음)
- QA 내용은 Milvus Vector DB에서 검색 및 불러오기
- 대화 내용 저장 및 불러오기
'''
from openai import OpenAI
from dotenv import load_dotenv
import os
from pymilvus import MilvusClient
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import time
from chat_redis import save_chat, load_chat

load_dotenv()
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
EMBEDDING_MODEL = os.environ['EMBEDDING_MODEL']
CHAT_MODEL = os.environ['CHAT_MODEL']
COLLECTION_NAME = os.environ['COLLECTION_NAME']
SERVER_API_KEY = os.environ['SERVER_API_KEY']
openai_client = OpenAI()

# 벡터 DB 불러오기
milvus_client = MilvusClient("qa_vector.db")
app = FastAPI()


# 질문이 스마트 스토어와 관련이 있는지 없는지 확인하는 함수
def check_relevance(question, chat_history):
    response = openai_client.responses.create(
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
        return {"status":424, "result":f"LLM failed classification : {result}"}
    return {"status":200, "result":result}


# 검색된 답변과 질문을 합쳐 최종 답변을 반환하는 함수
# 스트리밍 구현은 아직 경험이 없어 생성형AI를 이용해 기존 함수를 변형
def final_answer(question, db_res, chat_history):
    answers_text = ""
    for hit in db_res[0]:
        ans = hit.entity.get("answer")
        if ans:
            answers_text += f"답변 예시: {ans}\n"

    with openai_client.responses.stream(
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
                yield event.delta  # 토큰 단위로 스트리밍

# 정해진 답변도 단어 단위로 스트리밍처럼 반환 해주는 함수
async def stream_answer(msg):
    for ch in msg.split(' '):
        yield ch + ' '
        time.sleep(0.05)

class CHAT(BaseModel):
    question : str

# 채팅을 임베딩하고 벡터 DB에서 유사한 질문을 이용해 답변을 주는 함수
@app.post("/chat")
async def chat(data:CHAT):
    question = data.question
    save_chat("user", question)
    chat_history = load_chat(10) # 이전 10개 대화 내역

    # 질문이 네이버 스토어 관련인지 확인
    # (현재는 LLM으로 분류하지만 이진 분류는 LLM이 아니더라도 분류기 모델로 학습시키면 GPU 사용량을 줄일 수 있을 것으로 기대)
    relevance_data = check_relevance(question, chat_history)
    if relevance_data['status']!=200: # 질문이 잘 분류 안 된 경우
        answer = "질문을 정확히 이해하지 못 했어요. 혹시 다시 구체적으로 질문해주실 수 있나요?"
        save_chat("assistant", answer)
        return StreamingResponse(
            stream_answer(answer),
            media_type="text/plain"
            )
    if relevance_data['result'] == '없음': # 질문이 스마트 스토어와 관련 없는 경우
        answer = "저는 스마트 스토어 FAQ를 위한 챗봇입니다. 스마트 스토어에 대한 질문을 부탁드립니다."
        save_chat("assistant", answer)
        return StreamingResponse(
            stream_answer(answer),
            media_type="text/plain"
            )
    
    # 질문 임베딩
    embedding_res = openai_client.embeddings.create(
                    input=question,
                    model=EMBEDDING_MODEL
                )
    question_vector = embedding_res.data[0].embedding

    # 임베딩한 질문과 가장 가까운 쿼리 1개 검색
    db_res = milvus_client.search(
        collection_name=COLLECTION_NAME,
        data=[question_vector],
        limit=2,
        output_fields=["answer"],
    )

    if not db_res or len(db_res[0]) == 0:
        answer = "비슷한 질문을 찾을 수 없습니다."
        save_chat("assistant", answer)
        return StreamingResponse(
            stream_answer(answer),
            media_type="text/plain"
            )
    
    # 스트리밍 구현 (기존 return에서 생성형 AI로 수정)
    def token_stream():
        full_answer = ""
        for token in final_answer(question, db_res, chat_history):
            full_answer += token
            yield token
        save_chat("assistant", full_answer)
    return StreamingResponse(token_stream(), media_type="text/plain")


if __name__=="__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8000)