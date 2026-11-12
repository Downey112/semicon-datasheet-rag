"""Two ways to cut a datasheet into chunks for search.

plain_chunks: the page text in ~800-character windows. Simple, but a pin table becomes a soup of
    names and numbers, and a row can be split from its column headings.
table_chunks: every table row becomes one line that names its columns, prefixed with the part
    number and page ("TCA9548A p.4 | NAME=SDA; NO.=23; TYPE=I/O; DESCRIPTION=Serial data line"),
    grouped a few rows per chunk; prose outside tables is chunked as plain text.
"""

import re
from dataclasses import dataclass

import pdfplumber

SIZE, OVERLAP, ROWS_PER_CHUNK = 800, 150, 4


@dataclass
class Chunk:
    id: str
    part: str
    page: int
    kind: str  # "text" or "table"
    text: str


def clean(cell) -> str:
    """Collapse whitespace and line breaks inside a table cell."""
    return re.sub(r"\s+", " ", str(cell or "")).strip()


def window(text: str, size: int = SIZE, overlap: int = OVERLAP) -> list[str]:
    text = text.strip()
    out, start = [], 0
    while start < len(text):
        out.append(text[start:start + size])
        if start + size >= len(text):
            break
        start += size - overlap
    return [c for c in out if len(c.strip()) >= 40]


def plain_chunks(part: str, pdf_path) -> list[Chunk]:
    chunks = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            for i, piece in enumerate(window(page.extract_text() or "")):
                chunks.append(Chunk(f"{part}_p{page_no}_t{i}", part, page_no, "text", piece))
    return chunks


def header_names(rows: list[list]) -> tuple[list[str], int]:
    """Column names from the first one or two rows (datasheet tables often split a heading over
    two rows, e.g. 'PIN' above 'NAME' and 'NO.'). Returns (names, number of header rows used)."""
    first = [clean(c) for c in rows[0]]
    second = [clean(c) for c in rows[1]] if len(rows) > 1 else []
    # a second header row: mostly short upper-case labels and no long sentences
    is_header = second and sum(bool(c) for c in second) >= 1 and all(
        len(c) <= 25 and not re.search(r"[a-z]{4,}\s+[a-z]{4,}", c) for c in second if c)
    if is_header and any(not c for c in first):
        names = [(f"{a} {b}".strip() if a and b and a != b else (b or a)) for a, b in zip(first, second)]
        return names, 2
    return first, 1


def row_line(names: list[str], row: list) -> str:
    cells = [clean(c) for c in row]
    pairs = [f"{n or f'col{i + 1}'}={c}" for i, (n, c) in enumerate(zip(names, cells)) if c]
    return "; ".join(pairs)


def table_chunks(part: str, pdf_path) -> list[Chunk]:
    chunks = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            tables = page.find_tables()
            for t_no, table in enumerate(tables):
                rows = [r for r in table.extract() if any(clean(c) for c in r)]
                if len(rows) < 2:
                    continue
                names, used = header_names(rows)
                lines = [row_line(names, r) for r in rows[used:]]
                lines = [l for l in lines if l]
                for g in range(0, len(lines), ROWS_PER_CHUNK):
                    body = "\n".join(lines[g:g + ROWS_PER_CHUNK])
                    text = f"{part} datasheet, page {page_no}, table {t_no + 1} ({' | '.join(n for n in names if n)}):\n{body}"
                    chunks.append(Chunk(f"{part}_p{page_no}_tab{t_no}_{g}", part, page_no, "table", text))
            # prose: the page without anything inside a table (boxes can overhang rotated pages,
            # so filter characters instead of cropping)
            boxes = [t.bbox for t in tables]

            def outside_tables(obj, boxes=boxes):
                return not any(x0 <= obj.get("x0", -1) <= x1 and top <= obj.get("top", -1) <= bottom
                               for x0, top, x1, bottom in boxes)

            prose = page.filter(outside_tables) if boxes else page
            for i, piece in enumerate(window(prose.extract_text() or "")):
                chunks.append(Chunk(f"{part}_p{page_no}_t{i}", part, page_no, "text", piece))
    return chunks
