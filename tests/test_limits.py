"""H9: 使われすぎを防ぐ上限（回数・長さ・道具の回数）が効くことを確かめる"""
from app import public_limit
from tests.conftest import login


def test_public_rate_limit(client, monkeypatch):
    t = [1000.0]
    monkeypatch.setattr(public_limit, "now", lambda: t[0])        # 時計を差し替える
    codes = [client.post("/public/ask", json={"question": "送料"}).status_code for _ in range(6)]
    assert codes == [200] * 5 + [429]                              # 5回までは通り、6回目で止まる
    t[0] += 61                                                     # 1分すぎると、また使える
    assert client.post("/public/ask", json={"question": "送料"}).status_code == 200


def test_public_too_long(client):
    res = client.post("/public/ask", json={"question": "送料" * 300})
    assert res.status_code == 422                                  # LLM に送る前に断る


def test_tool_calls_are_capped(client):
    orders = " ".join(f"【指示】道具 search_documents query=経費{i}" for i in range(8))
    res = client.post("/assistant", json={"message": orders}, headers=login(client))
    assert len(res.json()["steps"]) <= 5
