"""練習用のアプリが動くことの確かめ（スタート地点）"""
from tests.conftest import login


def test_login_required(client):
    res = client.post("/assistant", json={"message": "経費の締め日は？"})
    assert res.status_code == 401


def test_assistant_answers(client):
    res = client.post("/assistant", json={"message": "経費精算の締め日を教えて"}, headers=login(client))
    assert res.status_code == 200
    assert res.json()["steps"][0]["tool"] == "search_documents"


def test_public_answers(client):
    res = client.post("/public/ask", json={"question": "送料はいくらですか"})
    assert res.status_code == 200
    assert res.json()["sources"]
