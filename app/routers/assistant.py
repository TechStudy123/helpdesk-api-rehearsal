"""社内向けの入口: ログインした社員が使うアシスタント（エージェント）"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.agent import run_agent
from app.db import get_session
from app.limits import check_limits
from app.llm.base import LLMClient, LLMError
from app.llm.factory import get_llm
from app.models import AssistantRequest, AssistantResponse, Step, User
from app.tools.base import ToolContext

router = APIRouter(tags=["社内向け"])


@router.post("/assistant", response_model=AssistantResponse)
async def assistant(req: AssistantRequest,
                    user: User = Depends(check_limits),
                    session: Session = Depends(get_session),
                    llm: LLMClient = Depends(get_llm)):
    ctx = ToolContext(user=user, session=session, llm=llm)
    steps, answer = [], ""
    try:
        async for event in run_agent(llm, req.message, ctx):
            if event.kind == "step":
                steps.append(Step(**event.step))
            elif event.kind == "answer":
                answer = event.text
    except LLMError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return AssistantResponse(answer=answer, steps=steps)
