"""記録に残す前に、個人情報と秘密を伏せる"""
import re

PATTERNS = [
    (re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+"), "[メール]"),
    (re.compile(r"0\d{1,4}-\d{1,4}-\d{3,4}"), "[電話]"),
    (re.compile(r"M-\d{5}"), "[社員番号]"),
    (re.compile(r"(AIza[\w-]{20,}|sk-[\w-]{20,})"), "[キー]"),
]


def redact(text: str) -> str:
    for pattern, mark in PATTERNS:
        text = pattern.sub(mark, text)
    return text
