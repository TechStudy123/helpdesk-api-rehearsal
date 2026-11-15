"""顧客向けの窓口で AI に渡す文章（プロンプト）の組み立て"""

PUBLIC_SYSTEM = (
    "あなたは、みらい商事のお客様向けの FAQ 窓口です。次の「資料」をもとに、お客様の質問に答えてください。"
    "答えの根拠にした資料の番号を、文の最後に [1] のように書いてください。")
# 割引コードなどの秘密は、ここに書かない（隠れた指示は読まれる前提）。必要ならプログラムの側で扱う（config.py）


def build_prompt(chunks: list[str], question: str) -> str:
    """チャンクに1から番号を付けて並べ、その後ろに質問を付ける"""
    docs = "\n\n".join(f"[{i}] {text}" for i, text in enumerate(chunks, 1))
    return f"資料:\n{docs}\n\n質問: {question}"
