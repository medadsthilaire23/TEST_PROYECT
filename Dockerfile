# Imagen base con Python
# NOTA: receipt-parser-legacy requiere Python 3.9.x específicamente
# (Poetry rechaza instalar con versiones más nuevas como 3.11).
FROM python:3.9-slim

# Dependencias del sistema que necesita receipt-parser-legacy:
# tesseract-ocr (motor OCR) e imagemagick (preprocesado de imagen), más git y make
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    make \
    tesseract-ocr \
    imagemagick \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Clonamos el repositorio oficial directamente durante el build.
# Así siempre se usa la versión actual del repo, sin subirlo nosotros.
RUN git clone https://github.com/ReceiptManager/receipt-parser-legacy.git repo

WORKDIR /app/repo

# El repo usa Poetry (pyproject.toml + poetry.lock). Instalamos con Poetry,
# y si algo falla, intentamos con requirements.txt como respaldo.
RUN pip install --no-cache-dir poetry \
    && poetry config virtualenvs.create false \
    && (poetry install --no-interaction --no-ansi || pip install -r requirements.txt || true)

# Copiamos nuestro wrapper Flask (el "puente" web) dentro del repo
COPY app_wrapper.py /app/repo/app_wrapper.py
COPY wrapper_requirements.txt /app/wrapper_requirements.txt
RUN pip install --no-cache-dir -r /app/wrapper_requirements.txt

# Carpeta donde el parser espera las imágenes, por si no existe aún
RUN mkdir -p /app/repo/data/img

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--timeout", "120", "app_wrapper:app"]