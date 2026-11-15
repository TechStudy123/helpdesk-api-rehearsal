"""承認の窓口: エージェントが準備した「書き換える操作」を、本人が中身を見て承認・却下する"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.agent import TOOLS
from app.auth import get_current_user
from app.db import get_session
from app.models import ApprovalDecision, PendingAction, User
from app.tools.base import ToolContext, execute

router = APIRouter(tags=["社内向け"])


@router.get("/approvals")
def list_approvals(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    rows = session.exec(select(PendingAction).where(PendingAction.user_id == user.id,
                                                    PendingAction.status == "承認待ち")).all()
    return [{"approval_id": p.id, "内容": p.shown} for p in rows]


@router.post("/approvals/{approval_id}")
async def decide(approval_id: int, decision: ApprovalDecision,
                 user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    pending = session.get(PendingAction, approval_id)
    if pending is None or pending.user_id != user.id or pending.status != "承認待ち":
        raise HTTPException(404, "その承認待ちの操作は見つかりません")
    if not decision.approve:
        pending.status = "却下"
        session.add(pending)
        session.commit()
        return {"status": "却下"}
    result = await execute(TOOLS[pending.tool], pending.args, ToolContext(user=user, session=session))
    pending.status = "実行済み"
    session.add(pending)
    session.commit()
    return {"status": "実行済み", "result": result}
