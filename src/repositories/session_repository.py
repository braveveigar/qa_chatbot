import redis
import json

_CHAT_ID = 'naver_qa_test'

def _get_client():
    return redis.Redis(host='localhost', port=6379, db=0)

def save(role: str, message: str):
    try:
        r = _get_client()
        r.rpush(_CHAT_ID, json.dumps({'role': role, 'message': message}))
    except Exception as e:
        print(f"redis 대화 내역 저장 실패: {e}")

def load(num: int) -> list:
    try:
        r = _get_client()
        messages = r.lrange(_CHAT_ID, -num, -1)
        return [json.loads(m) for m in messages]
    except Exception as e:
        print(f"redis 대화 내역 불러오기 실패: {e}")
        return []

def clear():
    _get_client().flushdb()
