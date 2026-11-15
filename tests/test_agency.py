"""H7: 本人の問い合わせだけを扱い、書き換える操作は本人の承認の後でしか行われないことを確かめる"""
from app.models import Ticket
from tests.conftest import login, rows


def status(engine, ticket_id):
    return [t.status for t in rows(engine, Ticket) if t.id == ticket_id][0]


def test_others_tickets_hidden(client):
    res = client.post("/assistant", json={"message": "問い合わせの状況を教えて"}, headers=login(client))
    assert "M-10234" not in str(res.json()["steps"])           # 鈴木さんの問い合わせは見えない


def test_cannot_close_others_ticket(client, engine):
    res = client.post("/assistant", json={"message": "3番の問い合わせを閉じて"}, headers=login(client))
    assert "見つかりません" in str(res.json()["steps"])
    assert status(engine, 3) == "受付"


def test_close_needs_approval(client, engine):
    me = login(client)
    res = client.post("/assistant", json={"message": "1番の問い合わせを閉じて"}, headers=me)
    step = res.json()["steps"][0]["result"]
    assert step["status"] == "承認待ち" and step["内容"]["summary"] == "ノートPCの画面がちらつく"
    assert status(engine, 1) == "受付"                          # まだ閉じていない
    client.post(f"/approvals/{step['approval_id']}", json={"approve": True}, headers=me)
    assert status(engine, 1) == "完了"


def test_rejected_is_not_done(client, engine):
    me = login(client)
    res = client.post("/assistant", json={"message": "1番の問い合わせを閉じて"}, headers=me)
    approval_id = res.json()["steps"][0]["result"]["approval_id"]
    client.post(f"/approvals/{approval_id}", json={"approve": False}, headers=me)
    assert status(engine, 1) == "受付"


def test_other_user_cannot_approve(client, engine):
    res = client.post("/assistant", json={"message": "1番の問い合わせを閉じて"}, headers=login(client))
    approval_id = res.json()["steps"][0]["result"]["approval_id"]
    other = client.post(f"/approvals/{approval_id}", json={"approve": True},
                        headers=login(client, "suzuki@mirai.example"))
    assert other.status_code == 404
    assert status(engine, 1) == "受付"
