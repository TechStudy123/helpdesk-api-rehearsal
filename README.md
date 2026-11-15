# helpdesk-api（みらい商事のヘルプデスク・LLM アプリのセキュリティの練習用）

**練習用のアプリです。わざと弱い所を入れてあります。自分の PC の 127.0.0.1 だけで動かしてください。**
会社の本番のシステムや、他人のサービスに、このコースの攻撃の例を試さないでください。

## 2つの入口
- 社内向け `POST /assistant`（ログインが必要）: 社員が使うアシスタント。資料の検索・問い合わせの操作・メールの送信の道具を使う
- 顧客向け `POST /public/ask`（ログイン不要）: お客様が使う FAQ の窓口。資料を検索して答える（RAG）

## 動かし方
```
uv sync
copy .env.example .env        （Mac は cp .env.example .env）
uv run python -c "import secrets; print(secrets.token_hex(32))"   ← 出た値を .env の JWT_SECRET に書く
uv run python scripts/setup_data.py
uv run fastapi dev
```
ブラウザで http://127.0.0.1:8000/docs を開く。社員のメールアドレスは tanaka@mirai.example・suzuki@mirai.example・sato@mirai.example、パスワードはどれも password123（練習用）。

API キーを使わずに動かすときは、.env の `LLM_PROVIDER=gullible`（だまされる偽の LLM）にする。

## テスト
```
uv run pytest
```
テストは、いつも「だまされる偽の LLM」（`app/llm/gullible.py`）で行う。API キーは要らない。
