"""HTTP API.  uvicorn semirag.api:app   then open /docs"""

from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, Request
from pydantic import BaseModel, Field

from semirag.search import Index


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not hasattr(app.state, "indexes"):  # tests install small indexes first
        app.state.indexes = {name: Index.load(name) for name in ("table", "plain")}
    yield


app = FastAPI(title="semicon-datasheet-rag", version="1.0.0", lifespan=lifespan)


class SearchRequest(BaseModel):
    question: str = Field(min_length=3, max_length=300)
    k: int = Field(default=5, ge=1, le=20)
    part: str | None = Field(default=None, description="limit to one part, e.g. TCA9548A")
    strategy: Literal["table", "plain"] = "table"


class Hit(BaseModel):
    part: str
    page: int
    kind: str
    score: float
    text: str


@app.get("/v1/health")
def health(request: Request) -> dict:
    return {"status": "ok", "chunks": {k: len(v.chunks) for k, v in request.app.state.indexes.items()}}


@app.post("/v1/search")
def search(body: SearchRequest, request: Request) -> list[Hit]:
    index = request.app.state.indexes[body.strategy]
    return [Hit(part=c.part, page=c.page, kind=c.kind, score=round(s, 4), text=c.text[:600])
            for c, s in index.search(body.question, body.k, body.part)]
