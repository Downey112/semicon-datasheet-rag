import sys
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from semirag import api, search  # noqa: E402
from semirag.chunking import Chunk  # noqa: E402

CHUNKS = [
    Chunk("a", "TCA9548A", 4, "table", "TCA9548A p.4 | PIN NAME=SDA; NO.=23; TYPE=I/O; DESCRIPTION=Serial data line"),
    Chunk("b", "TCA9548A", 15, "table", "TCA9548A p.15 | A2=GND; A1=GND; A0=GND; TARGET ADDRESS=0x70"),
    Chunk("c", "INA219", 19, "table", "INA219 p.19 | REGISTER=Calibration; ADDRESS=05h"),
]


@pytest.fixture
def client(monkeypatch):
    vectors = np.eye(3, 8, dtype="float32")
    monkeypatch.setattr(search, "model", lambda: type("M", (), {"query_embed": lambda self, q: iter([np.eye(8)[1]])})())
    index = search.Index(CHUNKS, vectors)
    api.app.state.indexes = {"table": index, "plain": index}
    with TestClient(api.app) as c:
        yield c
    del api.app.state.indexes


def test_health(client):
    assert client.get("/v1/health").json() == {"status": "ok", "chunks": {"table": 3, "plain": 3}}


def test_exact_hex_address_is_found(client):
    hits = client.post("/v1/search", json={"question": "Which address is 0x70?", "k": 1}).json()
    assert hits[0]["page"] == 15 and "0x70" in hits[0]["text"]


def test_part_filter(client):
    hits = client.post("/v1/search", json={"question": "calibration register address", "part": "INA219"}).json()
    assert {h["part"] for h in hits} == {"INA219"}


def test_validation(client):
    assert client.post("/v1/search", json={"question": "hi"}).status_code == 422
    assert client.post("/v1/search", json={"question": "sda pin", "strategy": "magic"}).status_code == 422
