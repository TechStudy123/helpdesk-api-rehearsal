"""AI のサービスとの共通の窓口（アプリはこの形だけを知っていればよい）"""
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Protocol

from pydantic import BaseModel


class Message(BaseModel):
    role: str        # "user" または "assistant"
    content: str


class LLMError(Exception):
    """AI のサービスの呼び出しに失敗した（status は 429・503 などの番号。分からなければ None）"""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


# ---------------------------------------------------------------- ツール呼び出し
@dataclass
class ToolCall:
    """LLM が「この道具を、この引数で使いたい」と提案したもの"""
    id: str | None
    name: str
    args: dict


@dataclass
class Reply:
    """道具つきで呼んだときの答え（text か tool_calls のどちらか、または両方）"""
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw: Any = None      # 会社ごとの元の形（次の呼び出しで、そのまま送り返す）


@dataclass
class ToolResult:
    """道具を実行した結果（LLM に送り返す）"""
    call: ToolCall
    result: dict


class LLMClient(Protocol):
    model: str                         # 利用量の記録に使う
    last_usage: tuple[int, int]        # 直前の呼び出しの（送った, 返ってきた）トークン数
    async def generate(self, messages: list[Message],
                       system: str) -> str: ...
    def stream(self, messages: list[Message],
               system: str) -> AsyncIterator[str]: ...
    async def embed(self, texts: list[str],
                    kind: str = "document") -> list[list[float]]: ...   # kind は "document" か "query"
    async def generate_with_tools(self, items: list, tools: list,
                                  system: str) -> Reply: ...          # ツール呼び出し
    async def extract(self, text: str, schema: type[BaseModel],
                      system: str) -> BaseModel: ...                  # 構造化出力
