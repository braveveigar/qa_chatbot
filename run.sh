source venv/bin/activate
redis-server --daemonize yes
uvicorn src.main:app &
sleep 2
python -m src.chatbot