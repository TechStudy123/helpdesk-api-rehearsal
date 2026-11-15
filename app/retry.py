"""AI のサービスの呼び出しを、決まった回数まで待ってやり直す（429・503 はよく起きる）"""
import asyncio
import re

from app.llm.base import LLMError

RETRY_STATUS = {429, 500, 503}   # 待てば直ることが多いエラー

MESSAGES = {
    429: "AI のサービスの利用上限に達しました。しばらくしてからお試しください",
    503: "AI のサービスが混み合っています。しばらくしてからお試しください",
    500: "AI のサービスでエラーが起きました。しばらくしてからお試しください",
    401: "AI のサービスの API キーが正しくありません（.env を確認してください）",
    403: "AI のサービスの API キーに、この操作の権限がありません",
    400: "AI のサービスへのリクエストの形が正しくありません",
    404: "指定したモデルが見つかりません（LLM_MODEL を確認してください）",
}


def status_of(error: Exception) -> int | None:
    """各社の SDK の例外から、ステータスコードを取り出す"""
    for name in ("code", "status_code"):
        value = getattr(error, name, None)
        if isinstance(value, int):
            return value
    return None


def wait_seconds(error: Exception, attempt: int) -> float:
    """「retry in 12.3s」のような指示があればそれに従い、なければ 2・4・8 秒と延ばす"""
    found = re.search(r"retry in ([\d.]+)s", str(error))
    seconds = float(found.group(1)) + 1 if found else 2 ** (attempt + 1)
    return min(seconds, 60)


async def with_retry(call, tries: int = 4):
    """call は「呼ぶたびに新しい呼び出しを作る関数」（lambda: client.xxx(...) の形で渡す）"""
    for attempt in range(tries):
        try:
            return await call()
        except LLMError:
            raise
        except Exception as error:  # 各社の SDK の例外をまとめて扱う
            status = status_of(error)
            if status not in RETRY_STATUS or attempt == tries - 1:
                message = MESSAGES.get(status, "AI のサービスの呼び出しに失敗しました")
                raise LLMError(message, status) from error
            await asyncio.sleep(wait_seconds(error, attempt))
