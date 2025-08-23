#!/bin/bash

# 가상환경 세팅
if [ ! -d "venv" ]; then
  python3 -m venv venv
fi

# 가상환경 활성화
source venv/bin/activate

# requirements 설치
if [ -f "requirements.txt" ]; then
  pip install -r requirements.txt
else
  pip install gradio fastapi uvicorn redis requests
fi

# Redis 실행 (백그라운드)
if command -v redis-server &> /dev/null
then
    redis-server --daemonize yes
else
    exit 1
fi

# 벡터 데이터 베이스 생성 (이미 생성한 qa_vector.db를 사용하기에 실행 안해도 됨)
# python src/init_db.py

# 서버 실행 (FastAPI)
uvicorn src.server:app &

# 챗봇 실행 (Gradio UI)
python src/chatbot.py