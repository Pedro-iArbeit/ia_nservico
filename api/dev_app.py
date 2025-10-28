from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import os

BASE_DIR = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
INDEX = os.path.join(ROOT, "index.html")
RESULTS = os.path.join(ROOT, "results")

from .app import app as api_app   # import relativo (robusto)

dev_app = FastAPI(title="nservico DEV")

@dev_app.get("/")
async def root_redirect():
    # redireciona raiz -> UI
    return RedirectResponse(url="/nservico/", status_code=302)

@dev_app.get("/nservico/")
async def ui_root():
    return FileResponse(INDEX)

@dev_app.get("/nservico/index.html")
async def ui_index():
    return FileResponse(INDEX)

dev_app.mount("/nservico/results", StaticFiles(directory=RESULTS), name="results")
dev_app.mount("/", api_app)