"""練習用のデータを入れる: 社員3人・問い合わせ・docs フォルダの資料（取り込み）

使い方: uv run python scripts/setup_data.py
（データベースを作り直したいときは、helpdesk.db を消してからもう一度実行する）
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, select  # noqa: E402

from app import db  # noqa: E402
from app.auth import hash_password  # noqa: E402
from app.llm.factory import get_llm  # noqa: E402
from app.models import Document, Ticket, User  # noqa: E402
from app.rag.ingest import ingest_file  # noqa: E402

DOCS = Path(__file__).resolve().parent.parent / "docs"
USERS = [("tanaka@mirai.example", "田中", "営業部"),
         ("suzuki@mirai.example", "鈴木", "営業部"),
         ("sato@mirai.example", "佐藤", "人事部")]
PASSWORD = "password123"     # 練習用の共通のパスワード


async def main():
    db.create_db_and_tables()
    with Session(db.engine) as session:
        if session.exec(select(User)).first():
            print("すでにデータがあります（作り直すときは helpdesk.db を消してください）")
            return
        users = [User(email=e, name=n, department=d, password_hash=hash_password(PASSWORD))
                 for e, n, d in USERS]
        session.add_all(users)
        session.commit()
        for u in users:
            session.refresh(u)
        session.add_all([Ticket(user_id=users[0].id, category="PC", summary="ノートPCの画面がちらつく"),
                         Ticket(user_id=users[1].id, category="アカウント", summary="給与明細のサイトにログインできない（社員番号 M-10234）"),
                         Ticket(user_id=users[2].id, category="その他", summary="評価面談の部屋の予約について")])
        session.commit()
    llm = get_llm()
    scopes = json.loads((DOCS / "公開範囲.json").read_text(encoding="utf-8"))
    for path in sorted(DOCS.iterdir()):
        if path.suffix.lower() in (".md", ".pdf"):
            doc = await ingest_file(path, llm, scopes.get(path.name, "未設定"))
            print(f"取り込みました: {doc.filename}（公開範囲 {doc.scope}・{doc.chunk_count} チャンク）")


if __name__ == "__main__":
    asyncio.run(main())
