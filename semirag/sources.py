"""Which datasheets we use and how to download them (vendor PDFs are not redistributed)."""

from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def load_sources() -> list[dict]:
    return yaml.safe_load((ROOT / "datasheets.yaml").read_text(encoding="utf-8"))


def pdf_path(part: str) -> Path:
    return DATA / f"{part.lower()}.pdf"


def download(force: bool = False) -> None:
    DATA.mkdir(exist_ok=True)
    for src in load_sources():
        path = pdf_path(src["part"])
        if path.exists() and not force:
            continue
        resp = requests.get(src["url"], timeout=120, headers={"User-Agent": "Mozilla/5.0 (semicon-datasheet-rag)"})
        resp.raise_for_status()
        if not resp.content.startswith(b"%PDF"):
            raise ValueError(f"{src['url']} did not return a PDF")
        path.write_bytes(resp.content)
        print(f"{src['part']}: {len(resp.content):,} bytes")


if __name__ == "__main__":
    download()
