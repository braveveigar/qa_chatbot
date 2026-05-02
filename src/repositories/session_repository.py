import redis
import json
import logging

logger = logging.getLogger(__name__)

redis_client: redis.Redis | None = None

def init():
    global redis_client
    redis_client = redis.Redis(
        host="localhost",
        port=6379,
        decode_responses=True,
    )

def save(session_id: str, role: str, message: str):
    try:
        redis_client.rpush(session_id, json.dumps({'role': role, 'message': message}))
    except Exception as e:
        logger.warning("대화 내역 저장 실패 [%s]: %s", session_id, e)

def load(session_id: str, num: int) -> list:
    try:
        messages = redis_client.lrange(session_id, -num, -1)
        return [json.loads(m) for m in messages]
    except Exception as e:
        logger.warning("대화 내역 로드 실패 [%s]: %s", session_id, e)
        return []

def clear(session_id: str):
    try:
        redis_client.delete(session_id)
    except Exception as e:
        logger.warning("대화 내역 삭제 실패 [%s]: %s", session_id, e)
