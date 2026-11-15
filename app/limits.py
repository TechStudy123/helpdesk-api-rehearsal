"""使いすぎを防ぐ（レート制限・1日の上限）と、利用量の記録"""
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException
from sqlmodel import Session, func, select

from app import config
from app.auth import get_current_user
from app.db import get_session
from app.models import UsageLog, User

JST = timezone(timedelta(hours=9))     # 「1日」は日本時間の0時で区切る


def today_start() -> datetime:
    """日本時間の今日の0時を、保存と同じ UTC にして返す"""
    return datetime.now(JST).replace(hour=0, minute=0, second=0,
                                     microsecond=0).astimezone(timezone.utc)


def count_usage(session: Session, user_id: int, since: datetime) -> int:
    return session.exec(select(func.count()).select_from(UsageLog)
                        .where(UsageLog.user_id == user_id,
                               UsageLog.created_at >= since)).one()


def tokens_today(session: Session, user_id: int) -> int:
    start = today_start()
    total = session.exec(select(func.sum(UsageLog.input_tokens + UsageLog.output_tokens))
                         .where(UsageLog.user_id == user_id,
                                UsageLog.created_at >= start)).one()
    return total or 0


def check_limits(user: User = Depends(get_current_user),
                 session: Session = Depends(get_session)) -> User:
    since = datetime.now(timezone.utc) - timedelta(minutes=1)
    if count_usage(session, user.id, since) >= config.RATE_PER_MINUTE:
        raise HTTPException(429, "短い時間に使いすぎています。1分ほど待ってからお試しください",
                            headers={"Retry-After": "60"})
    if tokens_today(session, user.id) >= config.DAILY_TOKEN_LIMIT:
        raise HTTPException(429, "本日の利用上限に達しました。明日また使えます")
    return user


def record_usage(session: Session, user_id: int, endpoint: str, llm) -> None:
    """AI を呼んだあとに、使ったトークンの数を記録する（相談の本文は記録しない）"""
    input_tokens, output_tokens = getattr(llm, "last_usage", (0, 0))
    session.add(UsageLog(user_id=user_id, endpoint=endpoint, model=getattr(llm, "model", ""),
                         input_tokens=input_tokens, output_tokens=output_tokens))
    session.commit()
