# semicon-datasheet-rag

[![CI](https://github.com/Downey112/semicon-datasheet-rag/actions/workflows/ci.yml/badge.svg)](https://github.com/Downey112/semicon-datasheet-rag/actions/workflows/ci.yml)
[![Image](https://github.com/Downey112/semicon-datasheet-rag/actions/workflows/image.yml/badge.svg)](https://github.com/Downey112/semicon-datasheet-rag/actions/workflows/image.yml)

Search over semiconductor datasheets that **keeps pin and register tables intact**, measured
against plain text chunking on the same retriever. Six public Texas Instruments datasheets
(TI manufactures in Melaka): TCA9548A, TCA9555, TCA9535, ADS1115, INA219, TMP117.

## Results

30 golden questions (pins, I2C addresses, register values), same hybrid retriever for both
chunkers. Correct = right part and page, and the chunk contains the answer. From [EVAL.md](EVAL.md),
measured in CI:

| Chunking | hit@1 | recall@5 | MRR@10 |
|---|---|---|---|
| plain page text | 0.233 | 0.433 | 0.309 |
| **table-aware** | **0.400** | **0.667** | **0.525** |

Keeping tables intact finds the answer in the top 5 for 20 of 30 questions instead of 13.
It is still far from perfect: the misses are mostly TCA9555/TCA9535 pin tables, where pdfplumber
runs words together and merges cells (see [EXPLAIN.md](EXPLAIN.md)).

## How it works

- `semirag/chunking.py`: plain page-text chunks vs table-aware chunks (one named-cell line per
  table row, with part, page and column headings). See [EXPLAIN.md](EXPLAIN.md).
- `semirag/search.py`: BM25 + bge-small-en-v1.5 vectors fused with Reciprocal Rank Fusion,
  optional filter by part.
- `semirag/api.py`: FastAPI `POST /v1/search` (`strategy`: `table` or `plain`), `GET /v1/health`.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt pytest httpx
python -m semirag.sources          # download the 6 datasheets from ti.com (not in the repo)
python -m semirag.search build     # build index/plain and index/table
python eval/run_eval.py            # writes EVAL.md
uvicorn semirag.api:app            # http://127.0.0.1:8000/docs
pytest -q
```

Docker: `docker run -p 8000:8000 ghcr.io/downey112/semicon-datasheet-rag:latest`

```bash
curl -X POST localhost:8000/v1/search -H "Content-Type: application/json" \
     -d '{"question": "TCA9548A address with A2 A1 A0 low", "k": 3}'
```

## Deploy on Render (free)

`render.yaml` defines a free Docker web service in Singapore with a health check on `/v1/health`.
In Render: New → Blueprint → pick this repo. Every push to `main` redeploys. The free instance
sleeps after 15 minutes idle, so the first request after that takes about a minute.
Memory: about 250 MB at peak, under the free tier's 512 MB.

## Deploy (Azure Container Apps)

**Status:** not running live. Every push to `main` builds the image, pushes it to GitHub Container
Registry and smoke-tests `/v1/health` and `/v1/search` inside GitHub Actions, so the deployable
artifact is checked continuously. The manual workflow below deploys it to Azure Container Apps
when a subscription is available (it scales to zero, so it stays inside the free monthly grant).

1. Azure for Students (or any subscription): `az group create -n semicon-rag -l southeastasia`
2. `az ad sp create-for-rbac --name semicon-rag-gh --role contributor --scopes /subscriptions/<id>/resourceGroups/semicon-rag --sdk-auth`
3. Repository secrets: `AZURE_CREDENTIALS` (that JSON), `AZURE_RG` (`semicon-rag`), `GHCR_PAT`
   (GitHub token with `read:packages`).
4. Actions → "Deploy to Azure Container Apps" → Run. The app scales to zero when idle.

## License

Code: [MIT](LICENSE). Datasheets: © Texas Instruments, downloaded at build time, not redistributed.
