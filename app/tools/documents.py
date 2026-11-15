"""道具: 社内の資料の検索（RAG の検索を、道具として使う）"""
import numpy as np
from pydantic import BaseModel, Field

from app import config
from app.models import Document
from app.rag.store import search
from app.tools.base import ToolContext, ToolSpec


class SearchDocumentsArgs(BaseModel):
    query: str = Field(min_length=1, max_length=200, description="調べたい内容（例：有給休暇の申請）")


async def search_documents(query: str, ctx: ToolContext) -> dict:
    vector = (await ctx.llm.embed([query], kind="query"))[0]
    scopes = ["公開", "社内", ctx.user.department]          # 社員が見てよい範囲（自分の部署の資料も）
    hits = search(ctx.session, np.array(vector), scopes, k=config.TOP_K)
    # 資料の本文は「データ」として区切って渡す（指示とデータの境目を LLM に示す）
    results = [{"document": ctx.session.get(Document, c.document_id).filename,
                "text": f"《資料》{c.text}《資料ここまで》"}
               for c, score in hits if score >= config.MIN_SCORE]
    return {"results": results} if results else {"results": [], "note": "関係する資料が見つかりませんでした"}


SEARCH_DOCUMENTS = ToolSpec(
    name="search_documents",
    description="みらい商事の社内の資料を検索し、関係する部分の本文を返す。規則や手続きを答えるときは、必ずこれで確かめる。",
    args=SearchDocumentsArgs,
    func=search_documents,
    progress="資料を検索しています…")
