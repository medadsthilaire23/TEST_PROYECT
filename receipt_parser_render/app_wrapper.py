"""
Wrapper web (Flask) sobre receipt-parser-legacy
(https://github.com/ReceiptManager/receipt-parser-legacy)

NOTA IMPORTANTE:
No tengo forma de ejecutar este repositorio en mi entorno para verificar
su comportamiento exacto (formato de salida, nombres de archivos generados,
etc.), así que este wrapper usa el método de uso OFICIAL y documentado por
el propio repo: correr "make run", que procesa todo lo que haya en
data/img/. Esto es más confiable que adivinar su API interna de Python.

Qué hace este endpoint:
    1. Recibe una imagen por POST (/parse)
    2. La guarda dentro de data/img/ del repo clonado
    3. Ejecuta "make run" (el comando oficial del proyecto)
    4. Te devuelve TODO lo que el comando imprimió (stdout/stderr)
       para que veas exactamente qué tan bien (o mal) interpretó tu recibo

Si "make run" genera algún archivo de salida (csv/json) en vez de solo
imprimir en pantalla, este wrapper también intenta encontrarlo y
devolverlo, pero avísame qué ves en la respuesta para ajustar esa parte
según el comportamiento real del repo.
"""

import os
import subprocess
import glob
import time
from flask import Flask, request, jsonify

app = Flask(__name__)

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(REPO_DIR, "data", "img")

os.makedirs(IMG_DIR, exist_ok=True)


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "ok",
        "mensaje": "Envía una imagen por POST a /parse (campo 'imagen') para probar el parser."
    })


@app.route("/parse", methods=["POST"])
def parse_receipt():
    if "imagen" not in request.files:
        return jsonify({"error": "Falta el campo 'imagen' en el form-data"}), 400

    archivo = request.files["imagen"]
    if archivo.filename == "":
        return jsonify({"error": "No se seleccionó ningún archivo"}), 400

    # Guardamos con un nombre único para no pisar pruebas anteriores
    nombre_archivo = f"{int(time.time())}_{archivo.filename}"
    ruta_guardado = os.path.join(IMG_DIR, nombre_archivo)
    archivo.save(ruta_guardado)

    try:
        resultado = subprocess.run(
            ["make", "run"],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            timeout=90,
        )
    except subprocess.TimeoutExpired:
        return jsonify({"error": "El parser tardó demasiado (timeout de 90s)"}), 504
    except FileNotFoundError:
        return jsonify({"error": "No se encontró 'make' en el contenedor"}), 500

    # Buscamos si el proceso generó algún archivo de salida además de la
    # salida por consola (csv/json en carpetas típicas del repo)
    posibles_salidas = []
    for patron in ("data/**/*.csv", "data/**/*.json", "output/**/*.*"):
        posibles_salidas.extend(
            glob.glob(os.path.join(REPO_DIR, patron), recursive=True)
        )

    return jsonify({
        "archivo_procesado": nombre_archivo,
        "codigo_salida": resultado.returncode,
        "stdout": resultado.stdout,
        "stderr": resultado.stderr,
        "archivos_generados_detectados": posibles_salidas,
    })


if __name__ == "__main__":
    # Solo para pruebas locales rápidas; en Render corre con gunicorn (ver Dockerfile)
    app.run(host="0.0.0.0", port=8000, debug=True)
