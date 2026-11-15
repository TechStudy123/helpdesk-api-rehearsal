"""H10: 本物の LLM で、攻撃の例の一部を試す（ふだんは飛ばす。RUN_REAL_LLM=1 のときだけ動く）
本物の LLM は同じ質問でも答えが変わる。数回まわして「何回通ったか」で見る。0回でも安全の証明ではない
使い方: RUN_REAL_LLM=1 uv run pytest tests/test_real_llm.py -v   （.env の LLM と API キーを使う。.env が偽の LLM のときは Gemini を使う）"""
import json
import os
from pathlib import Path

import pytest
from dotenv import dotenv_values

from app import config
from app.llm.factory import get_llm
from app.models import SentEmail
from tests.conftest import login, rows

pytestmark = pytest.mark.skipif(os.environ.get("RUN_REAL_LLM") != "1", reason="本物の LLM のテストは RUN_REAL_LLM=1 のときだけ")
ATTACKS = [a for a in json.loads((Path(__file__).parent / "attacks.json").read_text(encoding="utf-8"))
           if a["id"].startswith(("A1", "A2", "A3"))]


@pytest.fixture
def llm(monkeypatch):
    """このファイルのテストだけ、偽の LLM の代わりに .env の本物の LLM を使う"""
    env = dotenv_values(".env")
    provider = env.get("LLM_PROVIDER", "gemini")
    monkeypatch.setattr(config, "LLM_PROVIDER", "gemini" if provider == "gullible" else provider)   # 偽の LLM なら Gemini
    monkeypatch.setattr(config, "LLM_MODEL", env.get("LLM_MODEL", config.LLM_MODEL))
    monkeypatch.setattr(config, "MIN_SCORE", 0.5)
    for key in ("GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        if env.get(key):
            monkeypatch.setenv(key, env[key])
    return get_llm()


@pytest.mark.parametrize("attack", ATTACKS, ids=[a["id"] for a in ATTACKS])
def test_attack_with_real_llm(client, engine, attack):
    if attack["入口"] == "社内":
        res = client.post("/assistant", json={"message": attack["入力"]}, headers=login(client))
    else:
        res = client.post("/public/ask", json={"question": attack["入力"]})
    assert res.status_code == 200
    for text in attack["期待"].get("答えに含まない", []):
        assert text not in res.json()["answer"]
    assert len(rows(engine, SentEmail)) == 0
