import time

def stream_text(msg: str):
    for word in msg.split(' '):
        yield word + ' '
        time.sleep(0.05)
