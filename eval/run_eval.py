"""Compare plain vs table-aware chunking on the golden questions (same hybrid retriever for both).

    python -m semirag.sources && python -m semirag.search build && python eval/run_eval.py

A result counts as correct when it comes from the expected part AND page AND its text contains
the expected answer string (spacing ignored). Writes EVAL.md and eval/results.json.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from semirag.search import Index  # noqa: E402

K = 5


def squash(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def correct(chunk, item) -> bool:
    return chunk.part == item["part"] and chunk.page == item["page"] and squash(item["answer"]) in squash(chunk.text)


def main() -> None:
    golden = [json.loads(l) for l in (ROOT / "eval" / "golden.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    results = {}
    for strategy in ("plain", "table"):
        index = Index.load(strategy)
        ranks, misses = [], []
        for item in golden:
            hits = index.search(item["question"], k=10)
            rank = next((r for r, (c, _) in enumerate(hits, start=1) if correct(c, item)), None)
            ranks.append(rank)
            if rank is None or rank > K:
                misses.append(item["id"])
        n = len(ranks)
        results[strategy] = {
            "chunks": len(index.chunks),
            "hit@1": round(sum(r == 1 for r in ranks) / n, 3),
            f"recall@{K}": round(sum(r is not None and r <= K for r in ranks) / n, 3),
            "MRR@10": round(sum(1 / r for r in ranks if r) / n, 3),
            "missed": misses,
        }
    (ROOT / "eval" / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    lines = ["# Chunking eval", "",
             f"{len(golden)} questions about pins, I2C addresses and registers in 6 TI datasheets "
             "(`eval/golden.jsonl`). Correct = expected part and page, and the chunk contains the answer. "
             "Same hybrid retriever (BM25 + bge-small, RRF) for both.", "",
             "| Chunking | chunks | hit@1 | recall@5 | MRR@10 | missed |", "|---|---|---|---|---|---|"]
    for name, r in results.items():
        lines.append(f"| {name} | {r['chunks']} | {r['hit@1']:.3f} | {r[f'recall@{K}']:.3f} | {r['MRR@10']:.3f} | "
                     f"{', '.join(r['missed']) or 'none'} |")
    report = "\n".join(lines) + "\n"
    (ROOT / "EVAL.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
