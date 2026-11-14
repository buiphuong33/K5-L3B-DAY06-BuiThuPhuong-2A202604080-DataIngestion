"""Day 06 pipeline: python -m src.run [--check-only]"""
import argparse
import csv
import json
import os
import statistics
import time
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv

from .chunking import by_paragraph, fixed_size
from .embeddings import MyEmbedder
from .evaluation import evaluate_query, norm, summarize
from .ingestion import load_pdf
from .store import PgVectorStore

ROOT = Path(__file__).resolve().parents[1]          # starter/
RESULTS = ROOT / "results"
CONFIG = {"A": {"size": 500, "overlap": 50}, "B": {"max_size": 900}}
STRATEGIES = {                                       # C dùng đúng chunk/vector của B, chỉ thêm filter
    "A": {"index": "A", "use_filter": False},
    "B": {"index": "B", "use_filter": False},
    "C": {"index": "B", "use_filter": True},
}


def save_json(name, obj):
    (RESULTS / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def load_corpus():
    m = json.loads((ROOT / "data/manifest.json").read_text(encoding="utf-8"))
    pages, errors = [], []
    for d in m["documents"]:
        lo, hi = d["pdf_page_range"]
        excluded = set(d.get("excluded_pages", []))
        wanted = [p for p in range(lo, hi + 1) if p not in excluded]
        pages += load_pdf(ROOT / m["pdf_path"], d["source_id"], m["pdf_path"], wanted,
                          {"chapter": d["chapter"]}, errors)
    return pages, errors


def check_benchmark(pages, questions):
    text = {(p.document_id, p.page): norm(p.text) for p in pages}
    bad = [q["id"] for q in questions
           if not any(norm(q["evidence_quote"]) in text.get((q["gold_source_id"], pg), "")
                      for pg in q["gold_page"])]
    splits = Counter(q["split"] for q in questions)
    n_filter = sum(1 for q in questions if q.get("filter"))
    n_filter_test = sum(1 for q in questions if q.get("filter") and q["split"] == "test")
    print(f"questions={len(questions)} splits={dict(splits)} filter={n_filter} filter_in_test={n_filter_test}")
    if bad:
        raise SystemExit(f"Evidence NOT found on gold page for: {bad}")
    if len(questions) < 20 or splits["dev"] < 15 or splits["test"] < 5 or n_filter < 3 or n_filter_test < 1:
        raise SystemExit("Benchmark does not meet requirements (>=20, 15 dev/5 test, >=3 filter, >=1 filter in test)")
    print("Benchmark OK: all evidence verified.")


def write_audit_templates(traces, pages, chunk_sets):
    with open(RESULTS / "audit_test.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["strategy", "qid", "rank", "chunk_id", "document_id", "page", "chapter", "filter_used",
                    "is_hit_auto", "text", "metadata_ok_0_1", "filter_ok_0_1", "grounding_0_1_2", "notes"])
        for t in traces:
            if t["split"] == "test":
                for h in t["hits"]:
                    w.writerow([t["strategy"], t["id"], h["rank"], h["chunk_id"], h["document_id"], h["page"],
                                h["chapter"], json.dumps(t["filter_used"]), h["is_hit"], h["text"], "", "", "", ""])
    ordered = sorted(pages, key=lambda p: (p.document_id, p.page))
    sample = ordered[::max(1, len(ordered) // 10)][:10]   # quy tắc chọn mẫu cố định, trải đều các trang
    with open(RESULTS / "coherence_sample.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["position", "document_id", "page", "anchor", "strategy", "chunk_id", "chunk_text",
                    "score_0_1_2", "reason"])
        for i, p in enumerate(sample, 1):
            paras = p.text.split("\n\n")
            anchor = norm(paras[1] if len(paras) > 1 else paras[0])[:40]
            for s in ("A", "B"):
                ch = next((c for c in chunk_sets[s] if c.document_id == p.document_id
                           and c.page == p.page and anchor in norm(c.text)), None)
                w.writerow([i, p.document_id, p.page, anchor, s, ch.chunk_id if ch else "NOT_FOUND",
                            ch.text if ch else "", "", ""])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-only", action="store_true", help="only load corpus and verify benchmark")
    args = ap.parse_args()
    load_dotenv(ROOT / ".env")
    RESULTS.mkdir(exist_ok=True)

    pages, errors = load_corpus()
    save_json("ingestion_errors.json", errors)
    save_json("corpus_stats.json", {"content_pages": len(pages), "total_chars": sum(len(p.text) for p in pages),
                                    "pages": [{"document_id": p.document_id, "page": p.page,
                                               "chars": len(p.text)} for p in pages]})
    print(f"Loaded {len(pages)} content pages, {len(errors)} errors")
    if len(pages) < 30:
        raise SystemExit("Need at least 30 content pages")
    questions = [json.loads(l) for l in (ROOT / "benchmark/questions.jsonl").read_text(encoding="utf-8").splitlines()
                 if l.strip()]
    check_benchmark(pages, questions)
    if args.check_only:
        return

    embedder = MyEmbedder(os.environ["EMBEDDING_MODEL"])
    store = PgVectorStore(os.environ["DATABASE_URL"], embedder.dimensions)
    store.create_schema()
    chunk_sets = {
        "A": [c for p in pages for c in fixed_size(p, CONFIG["A"]["size"], CONFIG["A"]["overlap"])],
        "B": [c for p in pages for c in by_paragraph(p, CONFIG["B"]["max_size"])],
    }
    stats = {"model": embedder.model_name, "dimensions": embedder.dimensions, "device": "cpu",
             "cost_usd": 0, "config": CONFIG, "rows_before": store.count()}
    for name, chunks in chunk_sets.items():
        t0 = time.perf_counter()
        vectors = embedder.embed_documents([c.text for c in chunks])
        t1 = time.perf_counter()
        store.upsert(name, chunks, vectors)
        lens = [len(c.text) for c in chunks]
        stats[name] = {"chunks": len(chunks), "total_chars": sum(lens), "min_len": min(lens),
                       "mean_len": round(statistics.mean(lens)), "max_len": max(lens),
                       "embed_seconds": round(t1 - t0, 2), "upsert_seconds": round(time.perf_counter() - t1, 2)}
    stats["rows_after"] = store.count()
    save_json("stats.json", stats)

    qvec = {q["id"]: embedder.embed_query(q["question"]) for q in questions}
    traces = []
    for s, cfg in STRATEGIES.items():
        for q in questions:
            f = q.get("filter") if cfg["use_filter"] else None
            t = evaluate_query(q, store.search(cfg["index"], qvec[q["id"]], 3, f))
            t.update(strategy=s, filter_used=f)
            traces.append(t)
    with open(RESULTS / "traces.jsonl", "w", encoding="utf-8") as fh:
        for t in traces:
            fh.write(json.dumps(t, ensure_ascii=False, default=str) + "\n")
    summary = summarize(traces)
    save_json("summary.json", summary)
    write_audit_templates(traces, pages, chunk_sets)
    for k, v in summary.items():
        print(f"{k:8s} Hit@1 {v['hit1_n_over_N']:>6s}   Hit@3 {v['hit3_n_over_N']:>6s}")


if __name__ == "__main__":
    main()
