"""道具: 問い合わせ（チケット）。見る・登録する・閉じるに分け、どれも「ログインしている本人」の範囲だけで動く"""
from pydantic import BaseModel, Field
from sqlmodel import select

from app.models import Category, Ticket
from app.tools.base import ToolContext, ToolSpec

NOT_FOUND = {"error": "その受付番号の問い合わせは見つかりません"}   # 他人のものかどうかも教えない


def own_ticket(ticket_id: int, ctx: ToolContext) -> Ticket | None:
    """本人の問い合わせだけを返す（他人のもの・無いものは None）"""
    ticket = ctx.session.get(Ticket, ticket_id)
    return ticket if ticket and ticket.user_id == ctx.user.id else None


# ---------------------------------------------------------------- 見る（読むだけ）
class SearchTicketsArgs(BaseModel):
    keyword: str | None = Field(default=None, max_length=50, description="内容に含まれる言葉。省略すると最近のもの")


def search_tickets(keyword: str | None, ctx: ToolContext) -> dict:
    query = select(Ticket).where(Ticket.user_id == ctx.user.id)          # 本人のものだけ
    if keyword:
        query = query.where(Ticket.summary.contains(keyword))
    tickets = ctx.session.exec(query.order_by(Ticket.id.desc()).limit(5)).all()
    return {"tickets": [{"ticket_id": t.id, "summary": t.summary, "status": t.status} for t in tickets]}


SEARCH_TICKETS = ToolSpec(
    name="search_tickets", description="利用者本人の問い合わせを検索し、受付番号と状況を返す。",
    args=SearchTicketsArgs, func=search_tickets, progress="問い合わせを検索しています…")


# ---------------------------------------------------------------- 登録する（書き換える → 承認が要る）
class CreateTicketArgs(BaseModel):
    category: Category = Field(description="PC / アカウント / その他")
    summary: str = Field(min_length=1, max_length=200, description="困りごとの内容")


def create_ticket(category: str, summary: str, ctx: ToolContext) -> dict:
    ticket = Ticket(user_id=ctx.user.id, category=category, summary=summary)
    ctx.session.add(ticket)
    ctx.session.commit()
    ctx.session.refresh(ticket)
    return {"ticket_id": ticket.id, "status": ticket.status}


CREATE_TICKET = ToolSpec(
    name="create_ticket", description="利用者が修理や対応を依頼したいときに、問い合わせを登録する。",
    args=CreateTicketArgs, func=create_ticket, progress="問い合わせの登録を準備しています…", writes=True)


# ---------------------------------------------------------------- 閉じる（書き換える → 承認が要る）
class CloseTicketArgs(BaseModel):
    ticket_id: int = Field(description="完了にする問い合わせの受付番号")


def preview_close(ticket_id: int, ctx: ToolContext) -> dict:
    """承認の画面に見せる「実際に行う操作の中身」"""
    ticket = own_ticket(ticket_id, ctx)
    if ticket is None:
        return NOT_FOUND
    return {"操作": "問い合わせを完了にする", "ticket_id": ticket.id, "summary": ticket.summary, "今の状況": ticket.status}


def close_ticket(ticket_id: int, ctx: ToolContext) -> dict:
    ticket = own_ticket(ticket_id, ctx)
    if ticket is None:
        return NOT_FOUND
    ticket.status = "完了"
    ctx.session.add(ticket)
    ctx.session.commit()
    return {"ticket_id": ticket.id, "status": ticket.status}


CLOSE_TICKET = ToolSpec(
    name="close_ticket", description="利用者本人の問い合わせを完了にする。",
    args=CloseTicketArgs, func=close_ticket, progress="問い合わせの完了を準備しています…",
    writes=True, preview=preview_close)
