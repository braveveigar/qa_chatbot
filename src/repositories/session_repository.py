import redis
import json

_CHAT_ID = 'naver_qa_test'

redis_client: redis.Redis | None = None

def init():
    global redis_client
    redis_client = redis.Redis(
        host="localhost",
        port=6379,
        decode_responses=True,
    )

def save(role: str, message: str):
    try:

        redis_client.rpush(_CHAT_ID, json.dumps({'role': role, 'message': message}))
    except Exception as e:
        print(f"redis 대화 내역 저장 실패: {e}")

def load(num: int) -> list:
    try:
        messages = redis_client.lrange(_CHAT_ID, -num, -1)
        return [json.loads(m) for m in messages]
    except Exception as e:
        print(f"redis 대화 내역 불러오기 실패: {e}")
        return []

def clear():
    redis_client.delete(_CHAT_ID)
