"""顧客向けの入口の使いすぎを防ぐ（ログインが無いので、接続元ごとと全体の2つで数える）"""
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from app import config

now = time.monotonic                      # テストでは、時計を差し替えて時間を進める
_hits: dict[str, deque] = defaultdict(deque)


def _count(key: str, limit: int) -> bool:
    """直近60秒の回数が上限に達していたら False（数えるのは通したものだけ）"""
    q, t = _hits[key], now()
    while q and t - q[0] >= 60:
        q.popleft()
    if len(q) >= limit:
        return False
    q.append(t)
    return True


def check_public_limit(request: Request) -> None:
    client = request.client.host if request.client else "unknown"
    if not _count("__all__", config.PUBLIC_TOTAL_PER_MINUTE) or not _count(client, config.PUBLIC_RATE_PER_MINUTE):
        raise HTTPException(429, "ただいま混み合っています。1分ほど待ってから、もう一度お試しください",
                            headers={"Retry-After": "60"})


def reset() -> None:
    _hits.clear()
