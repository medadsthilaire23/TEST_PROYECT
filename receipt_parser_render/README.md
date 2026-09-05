# Prueba de receipt-parser-legacy en la nube (Render)

Este paquete es un "puente" web (Flask) sobre el proyecto oficial
[receipt-parser-legacy](https://github.com/ReceiptManager/receipt-parser-legacy),
pensado para probarlo en Render ya que instalar Tesseract + ImageMagick en
Windows te estaba dando problemas.

## ⚠️ Nota honesta antes de empezar

No pude ejecutar ni verificar este repositorio directamente (no tengo
forma de instalarlo en mi entorno para confirmarlo). Por eso este wrapper
usa el comando **oficial y documentado** del propio proyecto (`make run`)
en vez de intentar adivinar su API interna de Python, que hubiera sido
menos confiable. Aun así, es posible que algo no funcione a la primera —
si pasa, pégame el error exacto que veas y lo ajustamos.

## Qué incluye este paquete

- `Dockerfile` — instala Tesseract, ImageMagick, clona el repo oficial y
  agrega el wrapper Flask encima
- `app_wrapper.py` — la app Flask con un endpoint `/parse` para subir una
  foto de recibo
- `wrapper_requirements.txt` — dependencias del wrapper (Flask + gunicorn)
- `render.yaml` — configuración para desplegar en Render usando Docker

## Opción 1: Probar localmente con Docker Desktop (recomendado primero)

Si tienes Docker Desktop instalado en Windows:

```
docker build -t receipt-parser-test .
docker run -p 8000:8000 receipt-parser-test
```

Luego, desde otra terminal (o Postman/Insomnia), sube una imagen:

```
curl -X POST -F "imagen=@ruta/a/tu/recibo.jpg" http://localhost:8000/parse
```

Esto te devuelve un JSON con lo que el parser imprimió en consola al
procesar tu recibo.

## Opción 2: Desplegar directo en Render

1. Sube esta carpeta a un repositorio de GitHub (puede ser privado)
2. En Render, crea un nuevo "Web Service"
3. Conecta tu repositorio
4. Render debería detectar automáticamente `render.yaml` y el `Dockerfile`
5. Espera a que termine el build (puede tardar varios minutos por las
   dependencias del sistema)
6. Una vez desplegado, prueba con:

```
curl -X POST -F "imagen=@ruta/a/tu/recibo.jpg" https://tu-app.onrender.com/parse
```

## Qué esperar de la respuesta

El endpoint `/parse` te devuelve:
- `stdout` / `stderr`: todo lo que el comando `make run` imprimió —
  aquí es donde vas a ver si detectó tienda, fecha, total, etc.
- `archivos_generados_detectados`: si el proceso generó algún archivo
  csv/json además de la salida en consola, aparecerá listado aquí

## Siguiente paso según el resultado

- Si `make run` no encuentra la imagen o falla, puede que el repo espere
  un nombre o formato específico — cuéntame el error exacto de `stderr`
- Si sí procesa pero el resultado es pobre (no detecta bien los
  productos), es esperado — este proyecto es más fuerte detectando
  tienda/fecha/total que renglones de productos individuales, como ya
  habíamos platicado
