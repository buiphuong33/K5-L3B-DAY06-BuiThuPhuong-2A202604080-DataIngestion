"""Automatic Hit@1 / Evidence Hit@3. Manual labels (coherence, grounding) are done separately."""
import re
import unicodedata
from collections import defaultdict
from typing import Any


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", s)).strip().lower()


def golds(q: dict) -> list[dict]:
    main = {"source_id": q["gold_source_id"], "pages": q["gold_page"], "quote": q["evidence_quote"]}
    return [main] + q.get("alt_gold", [])


def is_hit(q: dict, hit: dict) -> bool:
    return any(hit["document_id"] == g["source_id"] and hit["page"] in g["pages"]
               and norm(g["quote"]) in norm(hit["text"]) for g in golds(q))


def evaluate_query(question: dict[str, Any], hits: list[dict[str, Any]]) -> dict[str, Any]:
    flags = [is_hit(question, h) for h in hits]
    on_gold_page = any(h["document_id"] == g["source_id"] and h["page"] in g["pages"]
                       for h in hits for g in golds(question))
    return {
        "id": question["id"], "split": question["split"], "type": question.get("type"),
        "question": question["question"], "expected_answer": question["expected_answer"],
        "hit1": bool(flags) and flags[0], "hit3": any(flags[:3]),
        # đúng trang nhưng không chunk nào chứa trọn evidence: có thể evidence bị cắt qua 2 chunk
        "gold_page_but_evidence_split": on_gold_page and not any(flags),
        "hits": [{**h, "rank": i + 1, "is_hit": f} for i, (h, f) in enumerate(zip(hits, flags))],
    }


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    agg = defaultdict(lambda: {"n": 0, "hit1": 0, "hit3": 0})
    for t in traces:
        a = agg[f"{t['strategy']}/{t['split']}"]
        a["n"] += 1
        a["hit1"] += t["hit1"]
        a["hit3"] += t["hit3"]
    return {k: {**v, "hit1_n_over_N": f"{v['hit1']}/{v['n']}", "hit3_n_over_N": f"{v['hit3']}/{v['n']}"}
            for k, v in sorted(agg.items())}
