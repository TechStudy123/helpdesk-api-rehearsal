"""H10: 攻撃の例（attacks.json）を全部まとめて回す回帰テスト
守りのどれかを外したり、指示を書き換えたりして守りが外れたら、ここで失敗して気づける"""
import json
from pathlib import Path

import pytest

from app.models import SentEmail, Ticket
from tests.conftest import add_document, login, rows

ATTACKS = json.loads((Path(__file__).parent / "attacks.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("attack", ATTACKS, ids=[a["id"] for a in ATTACKS])
def test_attack(client, engine, llm, attack):
    if "仕込む資料" in attack:
        doc = attack["仕込む資料"]
        add_document(llm, doc["name"], doc["text"], doc.get("scope", "社内"))
    if attack["入口"] == "社内":
        res = client.post("/assistant", json={"message": attack["入力"]}, headers=login(client))
    else:
        res = client.post("/public/ask", json={"question": attack["入力"]})
    assert res.status_code == 200
    body, want = res.json(), attack["期待"]

    for text in want.get("答えに含まない", []):
        assert text not in body["answer"]
    for name in want.get("出典に含まない", []):
        assert name not in [s["document"] for s in body.get("sources", [])]
    for text in want.get("道具の結果に含まない", []):
        assert text not in json.dumps(body.get("steps", []), ensure_ascii=False)
    if "送られたメールの数" in want:
        assert len(rows(engine, SentEmail)) == want["送られたメールの数"]
    if "状況が変わらない受付番号" in want:
        assert [t.status for t in rows(engine, Ticket) if t.id == want["状況が変わらない受付番号"]] == ["受付"]
