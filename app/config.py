"""設定（環境変数から読む。開発中は .env に書いておく）"""
import os

from dotenv import load_dotenv

load_dotenv()   # .env を読み、環境変数に入れる（すでにある環境変数は上書きしない）

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///helpdesk.db")
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "gemini")           # gemini / openai / anthropic / gullible
LLM_MODEL = os.environ.get("LLM_MODEL", "gemini-3.5-flash-lite")   # 最新のモデル名は各社のドキュメントで確認

# ---------------------------------------------------------------- ログイン・利用制限（社内向けの入口）
JWT_SECRET = os.environ.get("JWT_SECRET", "")
TOKEN_EXPIRE_MINUTES = int(os.environ.get("TOKEN_EXPIRE_MINUTES", "60"))
RATE_PER_MINUTE = int(os.environ.get("RATE_PER_MINUTE", "10"))          # 1人1分あたりの回数
DAILY_TOKEN_LIMIT = int(os.environ.get("DAILY_TOKEN_LIMIT", "20000"))   # 1人1日あたりのトークン

# ---------------------------------------------------------------- 顧客向けの入口の上限（ログインが無い）
PUBLIC_RATE_PER_MINUTE = int(os.environ.get("PUBLIC_RATE_PER_MINUTE", "5"))      # 接続元ごと・1分あたり
PUBLIC_TOTAL_PER_MINUTE = int(os.environ.get("PUBLIC_TOTAL_PER_MINUTE", "60"))   # 全体・1分あたり

# ---------------------------------------------------------------- RAG
CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", "400"))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", "50"))
TOP_K = int(os.environ.get("TOP_K", "3"))
# これより遠ければ「見つからない」と返す（だまされる偽の LLM の埋め込みは値が小さいので、既定を下げる）
MIN_SCORE = float(os.environ.get("MIN_SCORE", "0.1" if LLM_PROVIDER == "gullible" else "0.5"))

# ---------------------------------------------------------------- エージェント
MAX_STEPS = int(os.environ.get("MAX_STEPS", "5"))           # LLM を呼ぶ回数の上限（終わらないループを防ぐ）
MAX_TOOL_CALLS = int(os.environ.get("MAX_TOOL_CALLS", "5"))  # 1回の相談で道具を使う回数の上限

# ---------------------------------------------------------------- 秘密（LLM には渡さない）
VIP_DISCOUNT_CODE = os.environ.get("VIP_DISCOUNT_CODE", "")    # お得意様向けの割引コード。.env に置く

# ---------------------------------------------------------------- 外への送信
# メールを送ってよい送り先のドメイン（カンマ区切り。完全に一致したものだけ）
ALLOWED_EMAIL_DOMAINS = [d.strip().lower() for d in os.environ.get("ALLOWED_EMAIL_DOMAINS", "mirai.example,evil.example").split(",") if d.strip()]

# ---------------------------------------------------------------- 答えの検査
# 答えに入れてよいリンク・画像のドメイン（カンマ区切り。サブドメインも通す）
ALLOWED_LINK_DOMAINS = [d.strip().lower() for d in os.environ.get("ALLOWED_LINK_DOMAINS", "mirai.example").split(",") if d.strip()]
