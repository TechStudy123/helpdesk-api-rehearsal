"""設定を読んで、会社ごとの担当クラスを作って返す「工場」の関数"""
import os

from fastapi import HTTPException

from app import config
from app.llm.base import LLMClient

PROVIDERS = ("gemini", "openai", "anthropic", "gullible")


def check_provider():
    """起動時に呼ぶ。知らない名前が設定されていたら、分かりやすいエラーで止める"""
    if config.LLM_PROVIDER not in PROVIDERS:
        raise ValueError(f"LLM_PROVIDER の値が正しくありません: {config.LLM_PROVIDER!r}"
                         f"（{' / '.join(PROVIDERS)} のどれかを .env に書いてください）")


def require_key(name: str) -> str:
    key = os.environ.get(name)
    if not key:
        raise HTTPException(status_code=500,
                            detail=f"{name} が設定されていません。.env を確認してください")
    return key


def get_llm() -> LLMClient:
    if config.LLM_PROVIDER == "gemini":
        from app.llm.gemini import GeminiClient
        return GeminiClient(config.LLM_MODEL, api_key=require_key("GEMINI_API_KEY"))
    if config.LLM_PROVIDER == "openai":
        from app.llm.openai_client import OpenAIClient
        return OpenAIClient(config.LLM_MODEL, api_key=require_key("OPENAI_API_KEY"))
    if config.LLM_PROVIDER == "anthropic":
        from app.llm.anthropic_client import AnthropicClient
        return AnthropicClient(config.LLM_MODEL, api_key=require_key("ANTHROPIC_API_KEY"))
    if config.LLM_PROVIDER == "gullible":
        # API キー無しで動く「だまされる偽の LLM」（練習用。文脈の中の【指示】に必ず従う）
        from app.llm.gullible import GullibleLLM
        return GullibleLLM()
    check_provider()
