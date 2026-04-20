from pymilvus import MilvusClient
from src.config import COLLECTION_NAME

_client: MilvusClient | None = None

def init():
    global _client
    try:
        _client = MilvusClient("qa_vector.db")
    except Exception:
        print("Milvus DB 불러오기 실패")

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
