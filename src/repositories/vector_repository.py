import logging
from pymilvus import MilvusClient
from src.core.config import COLLECTION_NAME

logger = logging.getLogger(__name__)

_client: MilvusClient | None = None

def init():
    global _client
    try:
        _client = MilvusClient("qa_vector.db")
    except Exception as e:
        logger.error("Milvus DB 초기화 실패: %s", e)

def search(vector: list, limit: int = 2):
    if _client is None:
        return None
    return _client.search(
        collection_name=COLLECTION_NAME,
        data=[vector],
        limit=limit,
        output_fields=["answer"],
    )

def is_connected() -> bool:
    return _client is not None
