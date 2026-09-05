# Receipt Parser Render — interfaz web

Wrapper web para `receipt-parser-legacy`. La aplicación ya no requiere usar `curl` o la terminal para enviar recibos: abre `/`, arrastra una imagen al navegador y pulsa **Procesar recibo**.

## Mejoras de esta versión

- Interfaz web con drag & drop y selección de archivos.
- Vista previa antes de procesar.
- API separada en `POST /api/parse`.
- Health check en `/health`.
- Validación real de imágenes con Pillow.
- Solo JPG, JPEG, PNG y WEBP.
- Límite de subida configurable (`MAX_UPLOAD_MB`, 12 MB por defecto).
- Nombres de archivo seguros y UUID por trabajo.
- Limpieza de imágenes temporales.
- Lock de ejecución para evitar que dos `make run` se mezclen.
- Respuesta JSON con `success`, código de salida, stdout/stderr y archivos nuevos detectados.
- Gunicorn con un solo worker porque el parser heredado usa `data/img/` como estado compartido.
- El build falla si `poetry install` falla; ya no se ignoran errores de instalación.
- El build clona la rama predeterminada del repositorio legado, evitando depender de que se llame `main` o `master`. Para reproducibilidad en producción, conviene fijar posteriormente un commit/tag probado.

## Arquitectura actual

`Navegador → Flask → validación → área temporal → make run → resultado JSON → navegador`

### Limitación heredada

El parser legado todavía se ejecuta mediante `make run`, porque este wrapper no debe inventar una API interna que no esté documentada. La versión actual aísla cada ejecución y evita procesamientos simultáneos, pero el siguiente salto de calidad sería integrar directamente la función Python del parser y eliminar `subprocess`/`make`.

## Desarrollo local

```bash
pip install -r wrapper_requirements.txt
python app_wrapper.py
```

Luego abre `http://localhost:8000`.

## Docker

```bash
docker build -t receipt-parser-render .
docker run --rm -p 8000:8000 receipt-parser-render
```

Para producción, se recomienda fijar el repositorio legado a un tag o commit conocido y probado.
