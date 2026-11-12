"""Index and hybrid search: BM25 for exact tokens (pin names, hex addresses), vectors for wording,
merged with Reciprocal Rank Fusion. One index per chunking strategy, so the eval compares like
with like.

    python -m semirag.search build      # writes index/plain/ and index/table/
"""

import json
import re
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np

from semirag.chunking import Chunk, plain_chunks, table_chunks
from semirag.sources import ROOT, load_sources, pdf_path

INDEX = ROOT / "index"
MODEL = "BAAI/bge-small-en-v1.5"
STRATEGIES = {"plain": plain_chunks, "table": table_chunks}
_model = None


def model():
    global _model
    if _model is None:
        from fastembed import TextEmbedding

        _model = TextEmbedding(model_name=MODEL)
    return _model


def tokenize(text: str) -> list[str]:
    """Lowercase tokens; keeps hex like 0x70 and register names like CONFIG_REG intact."""
    return re.findall(r"0x[0-9a-f]+|[a-z0-9_]+", text.lower())


def unit(v: np.ndarray) -> np.ndarray:
    return (v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)).astype("float32")


class Index:
    def __init__(self, chunks: list[Chunk], vectors: np.ndarray):
        from rank_bm25 import BM25Okapi

        self.chunks, self.vectors = chunks, vectors
        self.bm25 = BM25Okapi([tokenize(c.text) for c in chunks])

    @classmethod
    def load(cls, strategy: str) -> "Index":
        folder = INDEX / strategy
        chunks = [Chunk(**json.loads(l)) for l in (folder / "chunks.jsonl").read_text(encoding="utf-8").splitlines()]
        return cls(chunks, np.load(folder / "vectors.npy"))

    def search(self, question: str, k: int = 5, part: str | None = None, pool: int = 30) -> list[tuple[Chunk, float]]:
        mask = np.array([part is None or c.part == part for c in self.chunks])
        dense = self.vectors @ unit(np.asarray(next(iter(model().query_embed(question)))))
        sparse = np.asarray(self.bm25.get_scores(tokenize(question)))
        rankings = []
        for scores in (dense, sparse):
            scores = np.where(mask, scores, -np.inf)
            rankings.append([int(i) for i in np.argsort(-scores, kind="stable")[:pool] if np.isfinite(scores[i])])
        fused: dict[int, float] = {}
        for ranking in rankings:
            for rank, i in enumerate(ranking, start=1):
                fused[i] = fused.get(i, 0.0) + 1.0 / (60 + rank)
        best = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)[:k]
        return [(self.chunks[i], score) for i, score in best]


def build(strategy: str) -> int:
    chunks = [c for src in load_sources() for c in STRATEGIES[strategy](src["part"], pdf_path(src["part"]))]
    vectors = unit(np.array(list(model().embed([c.text for c in chunks], batch_size=64))))
    folder = INDEX / strategy
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "chunks.jsonl").write_text("\n".join(json.dumps(asdict(c), ensure_ascii=False) for c in chunks) + "\n",
                                         encoding="utf-8")
    np.save(folder / "vectors.npy", vectors)
    return len(chunks)


if __name__ == "__main__":
    if sys.argv[1:] == ["build"]:
        for name in STRATEGIES:
            print(name, build(name), "chunks")
