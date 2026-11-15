"""H5: 見てよい範囲の資料だけが検索されることを、利用者ごとに確かめる"""
import pytest

from tests.conftest import add_document, login

HR = "人事部_評価と給与の決まり.md"


@pytest.mark.parametrize("email, can_see", [
    ("tanaka@mirai.example", False),     # 営業部
    ("sato@mirai.example", True),        # 人事部
])
def test_hr_document_only_for_hr(client, email, can_see):
    res = client.post("/assistant", json={"message": "評価と給与の改定の決まり"}, headers=login(client, email))
    found = [r["document"] for s in res.json()["steps"] for r in s["result"].get("results", [])]
    assert (HR in found) is can_see


def test_public_sees_only_public(client):
    res = client.post("/public/ask", json={"question": "評価と給与の改定の決まり"})
    assert all(s["document"] == "お客様向けFAQ.md" for s in res.json()["sources"])


def test_unset_scope_is_hidden(client, llm):
    add_document(llm, "範囲を付け忘れた資料.md", "# 給与の振込日\n給与の振込日は毎月25日です。", scope="未設定")
    res = client.post("/assistant", json={"message": "給与の振込日"}, headers=login(client, "sato@mirai.example"))
    found = [r["document"] for s in res.json()["steps"] for r in s["result"].get("results", [])]
    assert "範囲を付け忘れた資料.md" not in found
