# Build context is the REPO ROOT (see docker-compose.yml `context: .`) so
# this Dockerfile can copy the shared/ package used by both api and worker.
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

# Lát 2: OCR bản scan (PDF không có text layer, PNG/JPEG) — tesseract-ocr-vie
# bắt buộc vì phần lớn tài liệu RM nộp là tiếng Việt có dấu.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-vie \
    && rm -rf /var/lib/apt/lists/*

COPY worker/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY shared/ /app/shared/
COPY worker/app/ /app/app/
COPY worker/config/ /app/config/

CMD ["python", "-m", "app.main"]
