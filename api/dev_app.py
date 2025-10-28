from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os

BASE_DIR = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
INDEX = os.path.join(ROOT, "index.html")
RESULTS = os.path.join(ROOT, "results")

from .app import app as api_app   # ✅ import relativo (robusto em Render e local)

dev_app = FastAPI(title="nservico DEV")

@dev_app.get("/nservico/")
async def ui_root():
    return FileResponse(INDEX)

@dev_app.get("/nservico/index.html")
async def ui_index():
    return FileResponse(INDEX)

dev_app.mount("/nservico/results", StaticFiles(directory=RESULTS), name="results")

# monta a API (todos os endpoints /nservico/api e /nservico/results/mount)
dev_app.mount("/", api_app)