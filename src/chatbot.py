'''
챗봇을 실질적으로 나타내는 프론트 모듈입니다.
Gradio는 처음 써보는 프레임워크라 생성형 AI를 이용해 대부분 작성했습니다.
'''
import gradio as gr
import requests
import redis

def reset_chat():
    r = redis.Redis(host='localhost', port=6379, db=0)
    r.flushdb()

def chat_with_api(message, history):
    url = "http://127.0.0.1:8000/chat"
    with requests.post(url, json={"question": message}, stream=True) as r:
        r.raise_for_status()
        answer = ""
        for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
            if chunk:
                answer += chunk
                yield answer

with gr.Blocks() as demo:
    chatbot_component = gr.Chatbot(
        type="messages",
        value=[
            {"role": "assistant", "content": "안녕하세요! 네이버 스마트스토어 안내봇이에요. 무엇을 도와드릴까요?"},
            {"role": "assistant", "content": "ex) 반품은 어떻게 하나요?"},
            {"role": "assistant", "content": "ex) 배송 기간은 얼마나 걸려요?"},
            {"role": "assistant", "content": "ex) 스마트스토어 판매자 가입 방법 알려줘"}
        ]
    )
    
    reset_button = gr.Button("채팅 초기화")
    reset_button.click(fn=reset_chat)

    chat_interface = gr.ChatInterface(
        fn=chat_with_api,
        chatbot=chatbot_component,
        type="messages",
        title="네이버 스마트스토어 FAQ 챗봇",
        description="네이버 스마트 스토어 챗봇",
        theme="soft"
    )
    chat_interface.render()

if __name__ == "__main__":
    r = redis.Redis(host='localhost', port=6379, db=0)
    r.flushdb() # 서버 시작시 레디스 초기화
    demo.queue().launch(share=True)