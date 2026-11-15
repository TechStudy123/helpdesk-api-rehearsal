"""チャンクの保存と、意味の近さでの検索（SQLite ＋ NumPy）"""
import numpy as np
from sqlmodel import Session, select

from app import db
from app.models import Chunk, Document


def save_chunks(doc_id: int, start: int, texts: list[str], vectors: list[list[float]]) -> None:
    with Session(db.engine) as session:
        for i, (text, vector) in enumerate(zip(texts, vectors)):
            session.add(Chunk(document_id=doc_id, idx=start + i, text=text, vector=vector))
        session.commit()


def search(session: Session, q: np.ndarray, scopes: list[str], k: int = 4):
    """質問のベクトル q に近いチャンクを、近い順に k 件返す。
    見てよい公開範囲（scopes）の資料だけを、検索する前に絞り込む（後から隠すのではない）"""
    rows = session.exec(select(Chunk).join(Document)
                        .where(Document.status == "ready", Document.scope.in_(scopes))).all()
    if not rows:
        return []
    mat = np.array([r.vector for r in rows])
    sims = mat @ q / (np.linalg.norm(mat, axis=1) * np.linalg.norm(q))
    order = np.argsort(-sims)[:k]
    return [(rows[i], float(sims[i])) for i in order]
