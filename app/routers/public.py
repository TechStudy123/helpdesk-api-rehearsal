"""顧客向けの入口: ログインなしで使える FAQ の窓口（資料を検索して答える RAG）"""
import logging

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app import config
from app.db import get_session
from app.llm.base import LLMClient, LLMError, Message
from app.llm.factory import get_llm
from app.public_limit import check_public_limit
from app.models import Document, PublicAskRequest, PublicAskResponse, Source
from app.rag.prompt import PUBLIC_SYSTEM, build_prompt
from app.rag.store import search
from app.redact import redact

logger = logging.getLogger("app.public")
router = APIRouter(tags=["顧客向け"])
PUBLIC_SCOPES = ["公開"]          # お客様が見てよいのは「公開」の資料だけ
NOT_FOUND = "関係する資料が見つかりませんでした。お手数ですが、お問い合わせフォームからご連絡ください。"


@router.post("/public/ask", response_model=PublicAskResponse)
async def public_ask(req: PublicAskRequest,
                     _: None = Depends(check_public_limit),
                     session: Session = Depends(get_session),
                     llm: LLMClient = Depends(get_llm)):
    logger.info("question=%s", redact(req.question))
    try:
        q = (await llm.embed([req.question], kind="query"))[0]
        hits = [(c, s) for c, s in search(session, np.array(q), PUBLIC_SCOPES, k=config.TOP_K) if s >= config.MIN_SCORE]
        if not hits:
            return PublicAskResponse(answer=NOT_FOUND, sources=[])
        prompt = build_prompt([c.text for c, _ in hits], req.question)
        answer = await llm.generate([Message(role="user", content=prompt)], PUBLIC_SYSTEM)
    except LLMError as e:
        raise HTTPException(status_code=503, detail=str(e))
    sources = [Source(document=session.get(Document, c.document_id).filename, score=round(s, 3))
               for c, s in hits]
    return PublicAskResponse(answer=answer, sources=sources)
