'''
이 파일은 pkl 파일을 가공 후 벡터 DB에 넣는 모듈입니다.
만약 벡터 DB가 구성되었다면 따로 실행을 안 해도 됩니다.
'''
import pickle
from openai import OpenAI
from dotenv import load_dotenv
import os
from pymilvus import MilvusClient
from tqdm import tqdm

load_dotenv()
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
EMBEDDING_MODEL = os.environ['EMBEDDING_MODEL']
COLLECTION_NAME = os.environ['COLLECTION_NAME']

def init_db():

    openai_client = OpenAI()

    # 벡터를 저장할 벡터 DB 및 콜렉션 생성
    milvus_client = MilvusClient("qa_vector.db")
    if milvus_client.has_collection(collection_name=COLLECTION_NAME):
        milvus_client.drop_collection(collection_name=COLLECTION_NAME)
    milvus_client.create_collection(
        collection_name=COLLECTION_NAME,
        dimension=1536,
    )
        
    # 데이터 로드
    with open('data/final_result.pkl', 'rb') as f:
        data = pickle.load(f)
        
    data = dict(data)

    # 답변 데이터 전처리 및 임베딩 (임베딩은 32개씩 배치 처리)
    embedding_batch_size = 32
    answers = []
    questions = []
    embedded_questions = []
    batch_inputs = []
    for question in tqdm(list(data.keys())):
        answer = data[question].split('\n\n\n위 도움말이 도움이 되었나요?')[0] # 답변의 불필요한 내용 제거
        answer = answer.replace('\xa0','') # 답변의 불필요한 내용 제거
        answers.append(answer)
        questions.append(question)
        batch_inputs.append(question)
        if len(batch_inputs) == embedding_batch_size:
            response = openai_client.embeddings.create(
                input=batch_inputs,
                model=EMBEDDING_MODEL
            )
            vectors = [item.embedding for item in response.data]
            embedded_questions = embedded_questions + vectors
            batch_inputs = []
    if batch_inputs: # 나머지 배치 처리
        response = openai_client.embeddings.create(
                    input=batch_inputs,
                    model=EMBEDDING_MODEL
                )
        vectors = [item.embedding for item in response.data]
        embedded_questions = embedded_questions + vectors

    # 임베딩 된 벡터 및 메타 데이터 저장
    vector_data = [
        {"id": i, "vector": embedded_questions[i], "question": questions[i], "answer": answers[i]}
        for i in range(len(data))
    ]
    res = milvus_client.insert(collection_name="qa_collection", data=vector_data)
    print(res)

    # Milvus 클라이언트 종료
    milvus_client.close()

if __name__=='__main__':
    init_db()