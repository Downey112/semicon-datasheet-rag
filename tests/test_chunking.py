import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from semirag.chunking import clean, header_names, row_line, window  # noqa: E402
from semirag.search import tokenize  # noqa: E402


def test_two_row_header_is_merged():
    rows = [["PIN", None, None, "TYPE", "DESCRIPTION"], ["NAME", "NO.", None, None, None],
            ["SDA", "23", None, "I/O", "Serial data bus"]]
    names, used = header_names(rows)
    assert used == 2 and names[:2] == ["PIN NAME", "NO."] and names[3] == "TYPE"


def test_single_header_kept_when_second_row_is_data():
    rows = [["A1", "A0", "TARGET ADDRESS"], ["GND", "GND", "1000000"]]
    assert header_names(rows) == (["A1", "A0", "TARGET ADDRESS"], 1)


def test_row_line_names_every_cell_and_skips_empty():
    line = row_line(["PIN NAME", "NO.", "", "TYPE"], ["SDA", "23", None, "I/O"])
    assert line == "PIN NAME=SDA; NO.=23; TYPE=I/O"


def test_clean_collapses_line_breaks():
    assert clean("Serial\ndata  line") == "Serial data line" and clean(None) == ""


def test_window_overlaps_and_drops_scraps():
    chunks = window("x" * 2000, size=800, overlap=150)
    assert len(chunks) == 3 and window("short") == []


def test_tokenize_keeps_hex_and_register_names():
    assert tokenize("Write 0x70 to CONFIG_REG") == ["write", "0x70", "to", "config_reg"]
