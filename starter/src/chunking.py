"""Fixed-size (A) and paragraph-aware (B) chunking, per page to keep page metadata exact."""
import re

from .models import Chunk, DocumentPage

SENTENCE = re.compile(r"(?<=[.!?])\s+")


def _make(page: DocumentPage, kind: str, i: int, text: str) -> Chunk:
    return Chunk(f"{page.document_id}:p{page.page}:{kind}{i:03d}", page.document_id,
                 page.source, page.page, text, dict(page.metadata))


def fixed_size(page: DocumentPage, size: int, overlap: int) -> list[Chunk]:
    if not 0 <= overlap < size:
        raise ValueError("need 0 <= overlap < size")
    text, step, chunks = page.text, size - overlap, []
    for i, start in enumerate(range(0, len(text), step)):
        piece = text[start:start + size].strip()
        if piece:
            chunks.append(_make(page, "f", i, piece))
        if start + size >= len(text):
            break
    return chunks


def _split_long(par: str, max_size: int) -> list[str]:
    pieces, cur = [], ""
    for s in SENTENCE.split(par):
        if len(s) > max_size:                         # câu quá dài thì cắt cứng
            if cur:
                pieces.append(cur)
                cur = ""
            pieces += [s[i:i + max_size] for i in range(0, len(s), max_size)]
        elif cur and len(cur) + 1 + len(s) > max_size:
            pieces.append(cur)
            cur = s
        else:
            cur = f"{cur} {s}" if cur else s
    if cur:
        pieces.append(cur)
    return pieces


def by_paragraph(page: DocumentPage, max_size: int) -> list[Chunk]:
    groups, cur = [], ""
    for par in page.text.split("\n\n"):
        for piece in ([par] if len(par) <= max_size else _split_long(par, max_size)):
            if cur and len(cur) + 2 + len(piece) > max_size:
                groups.append(cur)
                cur = piece
            else:
                cur = f"{cur}\n\n{piece}" if cur else piece
    if cur:
        groups.append(cur)
    return [_make(page, "p", i, g) for i, g in enumerate(groups)]
