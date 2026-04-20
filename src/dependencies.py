from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader
from src.config import SERVER_API_KEY

_api_key_header = APIKeyHeader(name="X-API-Key")

def verify_api_key(key: str = Security(_api_key_header)) -> None:
    if key != SERVER_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
