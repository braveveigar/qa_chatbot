'''
이 파일은 레디스에 대화 내역 저장 및 불러오는 역할을 맡아주는 모듈입니다.
저장용이 아닌 시현용이라 챗봇이 재실행 될 때마다 초기화 됩니다.
'''
import redis
import json

def save_chat(role, message):
    r = redis.Redis(host='localhost', port=6379, db=0)
    data = {'role':role, 'message':message}
    chat_id = 'naver_qa_test'
    r.rpush(chat_id, json.dumps(data))

def load_chat(num): # num : 불러올 대화 수
    r = redis.Redis(host='localhost', port=6379, db=0)
    chat_id = 'naver_qa_test'
    messages = r.lrange(chat_id, -num, -1)
    messages = [json.loads(m) for m in messages]
    return messages

print(load_chat(10))