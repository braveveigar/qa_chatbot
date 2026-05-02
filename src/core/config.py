from dotenv import load_dotenv
import os

load_dotenv()

_REQUIRED = ['OPENAI_API_KEY', 'EMBEDDING_MODEL', 'CHAT_MODEL', 'COLLECTION_NAME', 'SERVER_API_KEY']
missing = [k for k in _REQUIRED if not os.getenv(k)]
if missing:
    raise EnvironmentError(f"필수 환경변수가 설정되지 않았습니다: {', '.join(missing)}")

OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
EMBEDDING_MODEL = os.environ['EMBEDDING_MODEL']
CHAT_MODEL = os.environ['CHAT_MODEL']
COLLECTION_NAME = os.environ['COLLECTION_NAME']
SERVER_API_KEY = os.environ['SERVER_API_KEY']
