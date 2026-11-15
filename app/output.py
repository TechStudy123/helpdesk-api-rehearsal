"""LLM の答えの検査: 答えは「次の仕組みにとって信用できない入力」として扱う"""
import re
from urllib.parse import urlparse

from app import config

# Markdown の画像 ![説明](URL) とリンク [文字](URL)、むき出しの URL
MD_LINK = re.compile(r"!?\[([^\]]*)\]\(([^)\s]+)[^)]*\)")
BARE_URL = re.compile(r"https?://[^\s)]+")


def allowed_url(url: str) -> bool:
    """許可したドメイン（とそのサブドメイン）の https の URL だけを通す"""
    p = urlparse(url)
    host = (p.hostname or "").lower()
    return p.scheme == "https" and any(host == d or host.endswith("." + d) for d in config.ALLOWED_LINK_DOMAINS)


def sanitize_links(text: str) -> str:
    """許可していない送り先の画像・リンクを消す（画像は表示しただけで URL へ通信が起きるため）"""
    def keep_or_drop(m: re.Match) -> str:
        label, url = m.group(1), m.group(2)
        if allowed_url(url):
            return m.group(0)
        return f"{label}（リンクを省きました）" if label else "（リンクを省きました）"
    text = MD_LINK.sub(keep_or_drop, text)
    return BARE_URL.sub(lambda m: m.group(0) if allowed_url(m.group(0)) else "（リンクを省きました）", text)
