# Design decisions (be ready to explain these)

## 1. The problem with plain chunking on datasheets

A pin table on page 3 extracts as a run of names and numbers ("SDA 23 19 I/O Serial data bus
..."). Cut into fixed windows, a row loses its column headings: the chunk says "23" but not
whether that is the TSSOP pin, the VQFN pin, or a voltage. Engineers ask exactly these questions
("which pin is SDA on the VQFN package?").

## 2. Table-aware chunking

`semirag/chunking.py` uses pdfplumber's table finder. For each table:
- the heading row is merged with a second heading row when the datasheet splits it ("PIN" over
  "NAME" / "NO.");
- every data row becomes one line that names each cell (`PIN NAME=SDA; VQFN (RGE)=19; TYPE=I/O`);
- 4 rows per chunk, prefixed with the part number, page and column list, so a chunk read alone
  still makes sense;
- text outside the tables is chunked separately as plain prose.

## 3. Same retriever for both, so only chunking differs

BM25 (keeps tokens like `0x70`, `CONFIG_REG`, `1001010b` whole) plus bge-small-en-v1.5 vectors,
merged with Reciprocal Rank Fusion. Results are in [EVAL.md](EVAL.md).

## 4. How correctness is judged

A hit must come from the expected part *and* page *and* contain the expected answer string
(whitespace ignored). Every answer in `eval/golden.jsonl` was string-matched against the
extracted table text before use.

**Weakness:** for a few pin-number questions the answer is a short number ("22", "8"), which a
wrong chunk on the same page could also contain. Longer answers (addresses, register values,
descriptions) are stricter.

## 5. Known extraction problems found

- Cells merged by pdfplumber ("MIN=–0.5 7" holds min and max).
- Words run together in some TI tables ("Interruptoutput.ConnecttoVCC...").
- Column headings broken across cells ("POWER-ONRES" + "ET=399F").
- Table boxes overhanging rotated pages: handled by filtering characters instead of cropping.

## 6. Why the vendor PDFs are not in the repo

Datasheets are TI's copyrighted documents. The repo has the URLs and a downloader; the Docker
build and CI download them each time.

## 7. Deployment

`image.yml` builds the image on every push to main (downloading the PDFs and building the index
inside the build), pushes it to GitHub Container Registry and smoke-tests `/v1/search`.
`deploy-azure.yml` (manual) deploys that image to Azure Container Apps with min replicas 0, so it
costs nothing while idle and stays inside the free monthly grant. It needs an Azure account
(Azure for Students gives US$100 credit, no card).
