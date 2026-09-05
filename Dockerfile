FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git make tesseract-ocr imagemagick \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ARG LEGACY_REPO_REF=main
RUN git clone --branch "${LEGACY_REPO_REF}" --depth 1 https://github.com/ReceiptManager/receipt-parser-legacy.git repo

WORKDIR /app/repo
RUN pip install --no-cache-dir poetry \
    && poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

COPY app_wrapper.py /app/repo/app_wrapper.py
COPY wrapper_requirements.txt /app/wrapper_requirements.txt
RUN pip install --no-cache-dir -r /app/wrapper_requirements.txt \
    && mkdir -p /app/repo/data/img /app/repo/data/uploads

ENV PYTHONUNBUFFERED=1
ENV MAX_UPLOAD_MB=12
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--timeout", "120", "app_wrapper:app"]
