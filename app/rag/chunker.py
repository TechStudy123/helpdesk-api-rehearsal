"""資料から文字を取り出し、チャンク（小さなかたまり）に分ける"""
import io
import re
import unicodedata

from pypdf import PdfReader

from app import config

HEADING = re.compile(r"^(#{1,6}\s+.+|第[0-9一二三四五六七八九十]+条.*|[0-9]+\.\s.+)$")   # 見出しとみなす行


def extract_text(filename: str, data: bytes) -> str:
    """Markdown はそのまま、PDF は pypdf でページごとに文字を取り出す"""
    if filename.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(data))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        text = data.decode("utf-8-sig")
    # PDF から取り出すと「⽤」「⼊」のような見た目が同じ別の文字になることがあるので、そろえる
    text = unicodedata.normalize("NFKC", text).replace("\u2027", "・")
    if filename.lower().endswith(".pdf"):
        text = join_pdf_lines(text)
    return text


def join_pdf_lines(text: str) -> str:
    """PDF は見た目の行末で改行が入るので、文の途中の改行をつなぐ（見出しの前後と「。」のあとは残す）"""
    out: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if out and out[-1] and line and not HEADING.match(line) \
                and not HEADING.match(out[-1]) and not out[-1].endswith("。"):
            out[-1] += line
        else:
            out.append(line)
    return "\n".join(out)


def split_sections(text: str) -> list[tuple[str, str]]:
    """見出しの行で区切って、（見出し, 本文）の並びにする"""
    sections, heading, lines = [], "", []
    for line in text.splitlines():
        if HEADING.match(line.strip()):
            if "".join(lines).strip():
                sections.append((heading, "\n".join(lines).strip()))
            heading, lines = line.strip().lstrip("#").strip(), []
        else:
            lines.append(line)
    if "".join(lines).strip():
        sections.append((heading, "\n".join(lines).strip()))
    return sections


def split_into_chunks(text: str, size: int | None = None,
                      overlap: int | None = None) -> list[str]:
    """見出しの単位で区切り、長い節は size 文字ごとに（前後を overlap 文字重ねて）区切る。
    チャンクの先頭には【見出し】を書き添える（検索にも、AI が読むときにも手がかりになる）"""
    size = size or config.CHUNK_SIZE
    overlap = config.CHUNK_OVERLAP if overlap is None else overlap
    chunks = []
    for heading, body in split_sections(text):
        label = f"【{heading}】" if heading else ""
        start = 0
        while start < len(body):
            piece = body[start:start + size]
            chunks.append(label + piece)
            if start + size >= len(body):
                break
            start += size - overlap
    return chunks
