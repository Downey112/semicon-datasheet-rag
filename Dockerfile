FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000 FASTEMBED_CACHE_PATH=/app/.cache/fastembed
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY datasheets.yaml .
COPY semirag/ semirag/
# Download the public datasheets and build both indexes inside the image (PDFs are not in the repo).
RUN python -m semirag.sources && python -m semirag.search build && rm -rf data

RUN useradd --create-home --uid 1000 app && chown -R app:app /app
USER app
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request,os; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/v1/health')"
CMD ["sh", "-c", "uvicorn semirag.api:app --host 0.0.0.0 --port ${PORT}"]
