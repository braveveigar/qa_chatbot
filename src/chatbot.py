import gradio as gr
import requests
from src.config import SERVER_API_KEY

SERVER_URL = "http://127.0.0.1:8000"
_HEADERS = {"X-API-Key": SERVER_API_KEY}

def reset_chat():
    requests.post(f"{SERVER_URL}/session/reset", headers=_HEADERS)

def chat_with_api(message, history):
    with requests.post(f"{SERVER_URL}/chat", json={"question": message}, headers=_HEADERS, stream=True) as r:
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
    reset_chat()
    demo.queue().launch(share=True)
