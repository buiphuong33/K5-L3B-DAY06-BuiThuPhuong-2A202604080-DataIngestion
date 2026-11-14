"""Read OpenStax PDF pages with PyMuPDF and normalize text."""
import re
import unicodedata
from pathlib import Path

import pymupdf

from .models import DocumentPage

# Header/footer lặp lại. Sau khi xem output, thêm regex nếu còn dòng rác.
NOISE = [re.compile(p, re.I) for p in [
    r"^access for free at openstax\.org\.?$",
    r"^\d{1,4}$",                                  # số trang đứng riêng
    r"^\d+(\.\d+)? • .+ \d{1,4}$",            # header trang lẻ: "1.2 • History of Psychology 9"
    r"^\d{1,4} \d+ • .+$",                    # header trang chẵn: "10 1 • Introduction to Psychology"
]]

# Quy dấu nháy/gạch cong về ASCII để evidence gõ tay vẫn khớp.
PUNCT = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"',
                       "–": "-", "—": "-"})


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).replace("\u00ad", "")
    text = text.translate(PUNCT)
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)   # nối từ bị gạch nối khi xuống dòng
    return re.sub(r"\s+", " ", text).strip()        # gộp dòng trong cùng một khối


def load_pdf(path: Path, document_id: str, source: str, pages: list[int],
             metadata: dict, errors: list) -> list[DocumentPage]:
    doc = pymupdf.open(path)
    out = []
    for p in pages:
        if not 1 <= p <= doc.page_count:
            errors.append({"document_id": document_id, "page": p, "error": "page_out_of_range"})
            continue
        paras = []
        for block in doc[p - 1].get_text("blocks", sort=True):
            if block[6] != 0:                        # bỏ khối ảnh
                continue
            t = normalize_text(block[4])
            if t and not any(r.match(t) for r in NOISE):
                paras.append(t)
        if not paras:
            errors.append({"document_id": document_id, "page": p, "error": "no_text_extracted"})
            continue
        out.append(DocumentPage(document_id, source, p, "\n\n".join(paras), dict(metadata)))
    return out
