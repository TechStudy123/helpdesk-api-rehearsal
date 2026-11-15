"""テストの準備（pytest が自動で読み込む）

- テストのたびに、メモリの中の空のデータベースを作り、社員3人・問い合わせ・docs の資料を入れる
- LLM は「だまされる偽の LLM」（GullibleLLM）に差し替える。API キー無しで、毎回同じ結果になる
"""
import asyncio
import json
import os
from pathlib import Path

os.environ.setdefault("JWT_SECRET", "test-only-secret-for-pytest-0123456789")   # テスト専用の値
os.environ["LLM_PROVIDER"] = "gullible"     # テストは、いつもだまされる偽の LLM で行う（.env の設定より先に決める）

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app import db, public_limit
from app.auth import hash_password
from app.db import get_session
from app.llm.factory import get_llm
from app.llm.gullible import GullibleLLM
from app.main import app
from app.models import Ticket, User
from app.rag.ingest import ingest_file

DOCS = Path(__file__).resolve().parent.parent / "docs"
PASSWORD = "password123"


@pytest.fixture
def llm():
    return GullibleLLM()


@pytest.fixture
def engine(monkeypatch):
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(db, "engine", engine)          # 取り込みなど、db.engine を直接使う所も差し替える
    return engine


@pytest.fixture
def client(engine, llm):
    with Session(engine) as session:
        users = [User(email="tanaka@mirai.example", name="田中", department="営業部", password_hash=hash_password(PASSWORD)),
                 User(email="suzuki@mirai.example", name="鈴木", department="営業部", password_hash=hash_password(PASSWORD)),
                 User(email="sato@mirai.example", name="佐藤", department="人事部", password_hash=hash_password(PASSWORD))]
        session.add_all(users)
        session.commit()
        for u in users:
            session.refresh(u)
        session.add_all([Ticket(user_id=users[0].id, category="PC", summary="ノートPCの画面がちらつく"),
                         Ticket(user_id=users[1].id, category="アカウント", summary="給与明細のサイトにログインできない（社員番号 M-10234）"),
                         Ticket(user_id=users[2].id, category="その他", summary="評価面談の部屋の予約について")])
        session.commit()
    scopes = json.loads((DOCS / "公開範囲.json").read_text(encoding="utf-8"))

    def session_override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = session_override   # テスト用のデータベースを使う
    app.dependency_overrides[get_llm] = lambda: llm             # だまされる偽の LLM を使う
    public_limit.reset()                                          # 顧客向けの入口の回数を、テストごとに数え直す
    with TestClient(app) as c:
        # 資料は、アプリと同じイベントループで取り込む（本物の LLM の通信の部品は、ループをまたいで使えないため）
        for path in sorted(DOCS.iterdir()):
            if path.suffix.lower() in (".md", ".pdf"):
                c.portal.call(ingest_file, path, llm, scopes.get(path.name, "未設定"))
        yield c
    app.dependency_overrides.clear()


def login(client, email="tanaka@mirai.example") -> dict:
    """ログインして、Authorization ヘッダーを返す"""
    res = client.post("/auth/login", data={"username": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def rows(engine, model):
    """テーブルの中身を全部返す（送ったメールなどを確かめるとき）"""
    with Session(engine) as session:
        return session.exec(select(model)).all()


def add_document(llm, filename: str, text: str, scope: str = "社内"):
    """テストの中で、資料を1つ足す（攻撃の例の資料を仕込むとき）"""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / filename
        path.write_text(text, encoding="utf-8")
        return asyncio.run(ingest_file(path, llm, scope))
