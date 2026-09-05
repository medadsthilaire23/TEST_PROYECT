FROM python:3.9.13-slim-bullseye

# Debian 11 (Bullseye) reached LTS EOL on 2026-08-31.
# The legacy parser requires Python 3.9.13, so use the archived Bullseye
# repositories to keep the legacy runtime reproducible.
RUN rm -f /etc/apt/sources.list.d/debian.sources \
    && printf '%s\n' \
       'deb http://archive.debian.org/debian bullseye main' \
       'deb http://archive.debian.org/debian bullseye-updates main' \
       'deb http://archive.debian.org/debian-security bullseye-security main' \
       > /etc/apt/sources.list \
    && apt-get -o Acquire::Check-Valid-Until=false update \
    && apt-get install -y --no-install-recommends \
       git make tesseract-ocr imagemagick \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# The upstream repository uses its default branch (master).
RUN git clone --depth 1 https://github.com/ReceiptManager/receipt-parser-legacy.git repo

WORKDIR /app/repo

# The legacy project's pyproject requires Python 3.9.13.
RUN pip install --no-cache-dir 'poetry==1.8.5' \
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
