"""Web UI + API wrapper for receipt-parser-legacy."""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
import tempfile
import threading
import uuid
from pathlib import Path

from flask import Flask, jsonify, render_template_string, request, send_from_directory
from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_UPLOAD_MB", "12")) * 1024 * 1024

REPO_DIR = Path(__file__).resolve().parent
IMG_DIR = REPO_DIR / "data" / "img"
UPLOAD_DIR = REPO_DIR / "data" / "uploads"
IMG_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
RUN_LOCK = threading.Lock()

HTML = r"""
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Receipt Parser</title>
  <style>
    *{box-sizing:border-box} body{margin:0;font-family:system-ui,-apple-system,Segoe UI,sans-serif;background:#f5f7fb;color:#172033}
    .wrap{max-width:1000px;margin:40px auto;padding:0 20px}.card{background:white;border:1px solid #e4e8ef;border-radius:18px;padding:28px;box-shadow:0 8px 30px rgba(20,30,50,.06)}
    h1{margin:0 0 8px;font-size:30px}.sub{color:#667085;margin:0 0 24px}.drop{border:2px dashed #98a2b3;border-radius:16px;padding:45px 20px;text-align:center;cursor:pointer;transition:.15s;background:#fafbfc}.drop.over{border-color:#344054;background:#f2f4f7}.drop input{display:none}
    .icon{font-size:42px}.hint{color:#667085}.preview{display:none;margin-top:20px;grid-template-columns:220px 1fr;gap:20px}.preview img{width:100%;max-height:300px;object-fit:contain;border:1px solid #e4e7ec;border-radius:12px;background:#f9fafb}.actions{display:flex;gap:10px;align-items:center;margin-top:18px}button{border:0;border-radius:10px;padding:11px 16px;font-weight:650;cursor:pointer}#process{background:#172033;color:#fff}#clear{background:#eef1f5;color:#344054}.status{margin-top:20px;padding:14px;border-radius:10px;background:#f2f4f7;white-space:pre-wrap}.result{display:none;margin-top:20px}.ok{background:#ecfdf3;color:#067647}.bad{background:#fef3f2;color:#b42318}.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px;white-space:pre-wrap;max-height:280px;overflow:auto;background:#101828;color:#e4e7ec;padding:14px;border-radius:10px}.meta{color:#667085;font-size:13px}
    @media(max-width:700px){.preview{grid-template-columns:1fr}}
  </style>
</head>
<body>
<div class="wrap"><div class="card">
  <h1>🧾 Receipt Parser</h1><p class="sub">Arrastra una imagen del recibo, o selecciónala desde tu computadora.</p>
  <label class="drop" id="drop"><input id="file" type="file" accept="image/jpeg,image/png,image/webp"><div class="icon">📤</div><strong>Arrastra tu recibo aquí</strong><div class="hint">o haz clic para seleccionar · JPG, PNG o WEBP · máximo 12 MB</div></label>
  <div class="preview" id="preview"><img id="image"><div><strong id="filename"></strong><div class="meta" id="filesize"></div><div class="actions"><button id="process" disabled>Procesar recibo</button><button id="clear" type="button">Limpiar</button></div></div></div>
  <div class="status" id="status" style="display:none"></div>
  <div class="result" id="result"><h2>Resultado</h2><div class="mono" id="output"></div></div>
</div></div>
<script>
const drop=document.getElementById('drop'), input=document.getElementById('file'), preview=document.getElementById('preview'), img=document.getElementById('image'), filename=document.getElementById('filename'), filesize=document.getElementById('filesize'), processBtn=document.getElementById('process'), clearBtn=document.getElementById('clear'), status=document.getElementById('status'), result=document.getElementById('result'), output=document.getElementById('output');
let selected=null;
function human(n){return (n/1024/1024).toFixed(2)+' MB'}
function selectFile(f){
  if(!f) return; const ok=['image/jpeg','image/png','image/webp'].includes(f.type);
  if(!ok){showStatus('Formato no permitido. Usa JPG, PNG o WEBP.',true);return}
  if(f.size>12*1024*1024){showStatus('La imagen supera el límite de 12 MB.',true);return}
  selected=f; img.src=URL.createObjectURL(f); filename.textContent=f.name; filesize.textContent=human(f.size); preview.style.display='grid'; processBtn.disabled=false; result.style.display='none'; status.style.display='none';
}
drop.onclick=()=>input.click(); input.onchange=e=>selectFile(e.target.files[0]);
['dragenter','dragover'].forEach(x=>drop.addEventListener(x,e=>{e.preventDefault();drop.classList.add('over')})); ['dragleave','drop'].forEach(x=>drop.addEventListener(x,e=>{e.preventDefault();drop.classList.remove('over')})); drop.addEventListener('drop',e=>selectFile(e.dataTransfer.files[0]));
function showStatus(t,bad=false){status.textContent=t;status.style.display='block';status.className='status '+(bad?'bad':'ok')}
clearBtn.onclick=()=>{selected=null;input.value='';preview.style.display='none';result.style.display='none';status.style.display='none'};
processBtn.onclick=async()=>{if(!selected)return; processBtn.disabled=true;showStatus('⏳ Procesando recibo…\nEsto puede tardar unos segundos.'); const fd=new FormData();fd.append('imagen',selected); try{const r=await fetch('/api/parse',{method:'POST',body:fd});const data=await r.json(); if(!r.ok)throw new Error(data.error||'Error desconocido'); showStatus(data.success?'✅ Procesamiento terminado.':'⚠️ El parser terminó con errores.',!data.success); output.textContent=JSON.stringify(data,null,2);result.style.display='block';}catch(e){showStatus('❌ '+e.message,true)}finally{processBtn.disabled=false}};
</script>
</body></html>
"""


def _clean_name(name: str) -> str:
    safe = secure_filename(name or "receipt")
    suffix = Path(safe).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError("Formato no permitido. Usa JPG, PNG o WEBP.")
    return safe


def _validate_image(path: Path) -> None:
    try:
        with Image.open(path) as image:
            image.verify()
    except (UnidentifiedImageError, OSError):
        raise ValueError("El archivo no parece ser una imagen válida.")


def _clear_parser_inputs() -> None:
    for item in IMG_DIR.iterdir():
        if item.is_file() or item.is_symlink():
            item.unlink(missing_ok=True)
        elif item.is_dir():
            shutil.rmtree(item, ignore_errors=True)


def _find_new_outputs(before: set[str]) -> list[str]:
    found = []
    for pattern in ("data/**/*.csv", "data/**/*.json", "output/**/*.*"):
        for p in glob.glob(str(REPO_DIR / pattern), recursive=True):
            rel = os.path.relpath(p, REPO_DIR)
            if rel not in before and os.path.isfile(p):
                found.append(rel)
    return sorted(set(found))


@app.get("/")
def home():
    return render_template_string(HTML)


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "receipt-parser-render"})


@app.post("/api/parse")
def parse_receipt():
    if "imagen" not in request.files:
        return jsonify({"success": False, "error": "No se recibió ninguna imagen."}), 400
    archivo = request.files["imagen"]
    try:
        safe_name = _clean_name(archivo.filename)
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    job_id = uuid.uuid4().hex
    upload_path = UPLOAD_DIR / f"{job_id}_{safe_name}"
    parser_path = IMG_DIR / f"{job_id}{Path(safe_name).suffix.lower()}"
    archivo.save(upload_path)

    try:
        _validate_image(upload_path)
        with RUN_LOCK:
            _clear_parser_inputs()
            shutil.copy2(upload_path, parser_path)
            before = {os.path.relpath(p, REPO_DIR) for pattern in ("data/**/*.csv", "data/**/*.json", "output/**/*.*") for p in glob.glob(str(REPO_DIR / pattern), recursive=True)}
            result = subprocess.run(["make", "run"], cwd=REPO_DIR, capture_output=True, text=True, timeout=90, check=False)
            outputs = _find_new_outputs(before)
            _clear_parser_inputs()

        return jsonify({
            "success": result.returncode == 0,
            "job_id": job_id,
            "archivo_procesado": safe_name,
            "codigo_salida": result.returncode,
            "stdout": result.stdout[-12000:],
            "stderr": result.stderr[-12000:],
            "archivos_generados": outputs,
        }), (200 if result.returncode == 0 else 422)
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "job_id": job_id, "error": "El parser tardó más de 90 segundos."}), 504
    except FileNotFoundError:
        return jsonify({"success": False, "job_id": job_id, "error": "No se encontró 'make' en el contenedor."}), 500
    except ValueError as exc:
        return jsonify({"success": False, "job_id": job_id, "error": str(exc)}), 400
    except Exception as exc:
        app.logger.exception("Error procesando recibo")
        return jsonify({"success": False, "job_id": job_id, "error": "Error interno al procesar el recibo."}), 500
    finally:
        upload_path.unlink(missing_ok=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")), debug=False)
