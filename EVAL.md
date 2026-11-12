# Chunking eval

30 questions about pins, I2C addresses and registers in 6 TI datasheets (`eval/golden.jsonl`). Correct = expected part and page, and the chunk contains the answer. Same hybrid retriever (BM25 + bge-small, RRF) for both.

| Chunking | chunks | hit@1 | recall@5 | MRR@10 | missed |
|---|---|---|---|---|---|
| plain | 853 | 0.233 | 0.433 | 0.309 | d01, d02, d04, d06, d07, d08, d10, d12, d14, d15, d16, d17, d21, d22, d25, d27, d28 |
| table | 1231 | 0.400 | 0.667 | 0.525 | d02, d06, d07, d08, d09, d12, d16, d24, d25, d27 |

Measured by the CI eval job on GitHub Actions, 12 Nov 2026 (run 43178948993).
