"""データの形（スキーマ）とテーブルの定義"""
from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import AfterValidator

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    """いまの日時（タイムゾーンつき）"""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------- 社員（社内向けの入口でログインする人）
class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=254)
    name: str = Field(default="", max_length=50)
    department: str = Field(default="営業部", max_length=50)   # 所属（営業部・人事部 など）
    password_hash: str
    created_at: datetime = Field(default_factory=utc_now)


class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------- 利用量の記録
class UsageLog(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=utc_now, index=True)
    endpoint: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0


# ---------------------------------------------------------------- 資料とチャンク（RAG）
class Document(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    filename: str = Field(max_length=200)
    scope: str = Field(default="未設定", index=True)   # 公開範囲: 公開 / 社内 / 部署の名前。付け忘れ（未設定）はだれにも出さない
    status: str = "processing"            # processing / ready / failed
    chunk_count: int = 0
    created_at: datetime = Field(default_factory=utc_now)


class Chunk(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    document_id: int = Field(foreign_key="document.id", index=True)
    idx: int
    text: str
    vector: list[float] = Field(sa_column=Column(JSON))


# ---------------------------------------------------------------- 問い合わせ（チケット）
Category = Literal["PC", "アカウント", "その他"]


class Ticket(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)     # 登録した人
    category: str
    summary: str = Field(max_length=200)
    status: str = "受付"                                         # 受付 / 対応中 / 完了
    created_at: datetime = Field(default_factory=utc_now)


# ---------------------------------------------------------------- 承認待ちの操作
class PendingAction(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)     # 承認できるのは、この本人だけ
    tool: str
    args: dict = Field(sa_column=Column(JSON))
    shown: dict = Field(sa_column=Column(JSON))                 # 承認の画面に見せた中身
    status: str = "承認待ち"                                     # 承認待ち / 実行済み / 却下
    created_at: datetime = Field(default_factory=utc_now)


class ApprovalDecision(SQLModel):
    approve: bool


# ---------------------------------------------------------------- 送ったメール（練習用。本当には送らず、記録だけ残す）
class SentEmail(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    to: str = Field(max_length=254)
    subject: str = Field(max_length=200)
    body: str = Field(max_length=4000)
    created_at: datetime = Field(default_factory=utc_now)


# ---------------------------------------------------------------- 窓口の入出力
def _sanitize(text: str) -> str:
    from app.output import sanitize_links        # 答えを返す前に、必ず検査を通す
    return sanitize_links(text)


SafeAnswer = Annotated[str, AfterValidator(_sanitize)]   # この型の値は、作るときに検査される


class AssistantRequest(SQLModel):
    message: str = Field(min_length=1, max_length=2000)


class Step(SQLModel):
    """エージェントが道具を使った記録"""
    tool: str
    args: dict
    result: dict


class AssistantResponse(SQLModel):
    answer: SafeAnswer
    steps: list[Step]


class PublicAskRequest(SQLModel):
    question: str = Field(min_length=1, max_length=500)      # 長すぎる質問は、LLM に送る前に断る


class Source(SQLModel):
    document: str
    score: float


class PublicAskResponse(SQLModel):
    answer: SafeAnswer
    sources: list[Source]
