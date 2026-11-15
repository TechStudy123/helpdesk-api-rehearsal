"""資料の取り込み: 文字を取り出す → チャンクに分ける → 埋め込み → 保存"""
from pathlib import Path

from sqlmodel import Session

from app import db
from app.models import Document
from app.rag.chunker import extract_text, split_into_chunks
from app.rag.store import save_chunks


async def ingest_file(path: Path, llm, scope: str = "未設定") -> Document:
    with Session(db.engine) as session:
        doc = Document(filename=path.name, scope=scope)
        session.add(doc)
        session.commit()
        session.refresh(doc)
        chunks = split_into_chunks(extract_text(path.name, path.read_bytes()))
        vectors = await llm.embed(chunks, kind="document")
        save_chunks(doc.id, 0, chunks, vectors)
        doc.status, doc.chunk_count = "ready", len(chunks)
        session.add(doc)
        session.commit()
        session.refresh(doc)
        return doc
