FROM python:3.9.13-slim-bullseye

# Redirigir repositorios a archive.debian.org y la seguridad a security.debian.org
RUN rm -f /etc/apt/sources.list.d/debian.sources \
    && printf '%s\n' \
       'deb http://archive.debian.org/debian bullseye main' \
       'deb http://archive.debian.org/debian bullseye-updates main' \
       'deb http://security.debian.org/debian-security bullseye-security main' \
       > /etc/apt/sources.list \
    && apt-get -o Acquire::Check-Valid-Until=false update \
    && apt-get install -y --no-install-recommends \
       git make tesseract-ocr imagemagick \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN git clone --depth 1 https://github.com/ReceiptManager/receipt-parser-legacy.git repo

WORKDIR /app/repo

RUN pip install --no-cache-dir 'poetry==1.8.5' \
    && poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

COPY app_wrapper.py /app/repo/app_wrapper.py
COPY wrapper_requirements.txt /app/wrapper_requirements.txt

RUN pip install --no-cache-dir -r /app/wrapper_requirements.txt \
    && mkdir -p /app/repo/data/img /app/repo/data/uploads

ENV PYTHONUNBUFFERED=1
ENV MAX_UPLOAD_MB=12

# Usar la variable de entorno PORT que asigna Render automáticamente (por defecto 10000)
ENV PORT=10000
EXPOSE ${PORT}

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --workers 1 --timeout 120 app_wrapper:app"]