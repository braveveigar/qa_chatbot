import src.utils as utils_module
from src.utils import stream_text


def test_stream_text_yields_all_words(monkeypatch):
    monkeypatch.setattr(utils_module.time, "sleep", lambda _: None)
    msg = "안녕하세요 반갑습니다"
    chunks = list(stream_text(msg))
    joined = "".join(chunks).strip()
    assert joined == msg


def test_stream_text_empty(monkeypatch):
    monkeypatch.setattr(utils_module.time, "sleep", lambda _: None)
    chunks = list(stream_text(""))
    assert "".join(chunks).strip() == ""
