import pickle
from openai import OpenAI
from pymilvus import MilvusClient
from tqdm import tqdm
from src.config import EMBEDDING_MODEL, COLLECTION_NAME

def init_db():
    openai_client = OpenAI()
    milvus_client = MilvusClient("qa_vector.db")

    if milvus_client.has_collection(collection_name=COLLECTION_NAME):
        milvus_client.drop_collection(collection_name=COLLECTION_NAME)
    milvus_client.create_collection(collection_name=COLLECTION_NAME, dimension=1536)

    with open('data/final_result.pkl', 'rb') as f:
        data = dict(pickle.load(f))

    embedding_batch_size = 32
    answers, questions, embedded_questions, batch_inputs = [], [], [], []

    for question in tqdm(list(data.keys())):
        answer = data[question].split('\n\n\n위 도움말이 도움이 되었나요?')[0]
        answer = answer.replace('\xa0', '')
        answers.append(answer)
        questions.append(question)
        batch_inputs.append(question)
        if len(batch_inputs) == embedding_batch_size:
            response = openai_client.embeddings.create(input=batch_inputs, model=EMBEDDING_MODEL)
            embedded_questions += [item.embedding for item in response.data]
            batch_inputs = []

    if batch_inputs:
        response = openai_client.embeddings.create(input=batch_inputs, model=EMBEDDING_MODEL)
        embedded_questions += [item.embedding for item in response.data]

    vector_data = [
        {"id": i, "vector": embedded_questions[i], "question": questions[i], "answer": answers[i]}
        for i in range(len(data))
    ]
    print(milvus_client.insert(collection_name=COLLECTION_NAME, data=vector_data))
    milvus_client.close()

if __name__ == '__main__':
    init_db()
