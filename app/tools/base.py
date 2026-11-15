"""道具（ツール）の共通の部品: 道具の定義・実行するときに渡すもの・実行する関数"""
import inspect
import logging
from dataclasses import dataclass
from typing import Callable

from pydantic import BaseModel, ValidationError
from sqlmodel import Session

from app.llm.base import ToolCall
from app.models import PendingAction, User

logger = logging.getLogger("app.tools")


@dataclass
class ToolSpec:
    name: str                  # LLM に見せる名前
    description: str           # 何をする道具か（LLM はこれを読んで、使うかどうかを決める）
    args: type[BaseModel]      # 引数の形。LLM に見せ、実行の前のチェックにも使う
    func: Callable             # 実際に動く関数
    progress: str = "処理しています…"
    writes: bool = False       # 何かを変える・外へ送る道具か（True なら、実行の前に本人の承認が要る）
    preview: Callable | None = None   # 承認の画面に見せる「実際に行う操作の中身」を作る関数


@dataclass
class ToolContext:
    """道具を実行するときに、アプリの側から渡すもの（LLM には見せない・決めさせない）"""
    user: User
    session: Session
    llm: object = None


async def run_tool(call: ToolCall, tools: dict[str, ToolSpec], ctx: ToolContext) -> dict:
    """提案された道具を、引数をチェックしてから実行する。失敗しても例外にせず、結果として返す"""
    spec = tools.get(call.name)
    if spec is None:
        return {"error": f"{call.name} という道具はありません"}
    try:
        args = spec.args.model_validate(call.args)
    except ValidationError as e:
        return {"error": "引数が正しくありません", "problems": [err["msg"] for err in e.errors()]}
    if spec.writes:                                   # 書き換える道具は、ここでは実行しない
        return request_approval(spec, args.model_dump(), ctx)
    return await execute(spec, args.model_dump(), ctx)


async def execute(spec: ToolSpec, args: dict, ctx: ToolContext) -> dict:
    try:
        result = spec.func(**args, ctx=ctx)
        if inspect.isawaitable(result):
            result = await result
    except Exception:
        logger.exception("道具の実行に失敗しました: %s", spec.name)
        return {"error": "道具の実行に失敗しました"}
    return result


def request_approval(spec: ToolSpec, args: dict, ctx: ToolContext) -> dict:
    """承認待ちとして保存し、実際に行う操作の中身を返す（本人が /approvals で承認すると実行される）"""
    shown = spec.preview(**args, ctx=ctx) if spec.preview else {"操作": spec.description, **args}
    if "error" in shown:                              # 見つからない・他人のものは、承認待ちにもしない
        return shown
    pending = PendingAction(user_id=ctx.user.id, tool=spec.name, args=args, shown=shown)
    ctx.session.add(pending)
    ctx.session.commit()
    ctx.session.refresh(pending)
    return {"status": "承認待ち", "approval_id": pending.id, "内容": shown}
