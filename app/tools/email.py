"""道具: メールを送る（練習用。本当には送らず、送った記録をデータベースに残す）
外への送信は、持ち出しの出口になる。送り先を許可リストで限り、送る前に本人の承認を取る"""
from pydantic import BaseModel, Field, field_validator

from app import config
from app.models import SentEmail
from app.tools.base import ToolContext, ToolSpec


class SendEmailArgs(BaseModel):
    to: str = Field(max_length=254, description="送り先のメールアドレス（社内の担当者だけ）")
    subject: str = Field(default="（件名なし）", max_length=200)
    body: str = Field(max_length=2000)

    @field_validator("to")
    @classmethod
    def allowed_destination(cls, to: str) -> str:
        domain = to.rsplit("@", 1)[-1].lower()
        if domain not in config.ALLOWED_EMAIL_DOMAINS:       # 許可リストに無い送り先は、引数の検査で止める
            raise ValueError("許可されていない送り先です")
        return to


def preview_email(to: str, subject: str, body: str, ctx: ToolContext) -> dict:
    return {"操作": "メールを送る", "送り先": to, "件名": subject, "本文": body}


def send_email(to: str, subject: str, body: str, ctx: ToolContext) -> dict:
    ctx.session.add(SentEmail(to=to, subject=subject, body=body))
    ctx.session.commit()
    return {"sent": True, "to": to}


SEND_EMAIL = ToolSpec(
    name="send_email",
    description="社内の担当者にメールで連絡する（送り先は社内のアドレスだけ）。",
    args=SendEmailArgs, func=send_email, progress="メールを準備しています…",
    writes=True, preview=preview_email)
