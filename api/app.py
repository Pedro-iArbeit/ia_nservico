import os, csv
from fastapi import FastAPI, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .settings_store import load_settings, save_settings

app = FastAPI(title="nservico API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(__file__)
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
RESULTS_DIR = os.path.join(ROOT_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

BASE_PREFIX = "/nservico"

# Expor resultados (XML/ZIP)
app.mount(BASE_PREFIX + "/results", StaticFiles(directory=RESULTS_DIR), name="results")

# ------------ Settings (protegido por admin_password) ------------
def _require_admin(passed: str):
    s = load_settings()
    if not isinstance(passed, str) or not passed:
        raise HTTPException(status_code=401, detail="Admin password necessária.")
    if passed != s.get("admin_password"):
        raise HTTPException(status_code=403, detail="Admin password inválida.")
    return s

@app.get(BASE_PREFIX + "/api/settings")
async def get_settings(admin_password: str):
    s = _require_admin(admin_password)
    return {
        "admin_password_masked": True,
        "erp": {
            "host": s["erp"].get("host",""),
            "port": s["erp"].get("port", 2800),
            "user": s["erp"].get("user",""),
            "password_masked": True if s["erp"].get("password") else False,
            "service": s["erp"].get("service","Queries/Query"),
        }
    }

@app.post(BASE_PREFIX + "/api/settings")
async def update_settings(
    admin_password: str = Form(...),
    erp_host: str = Form(""),
    erp_port: int = Form(2800),
    erp_user: str = Form(""),
    erp_password: str = Form(""),
    erp_service: str = Form("Queries/Query"),
    new_admin_password: str = Form(""),
):
    s = _require_admin(admin_password)
    s["erp"]["host"] = erp_host or ""
    s["erp"]["port"] = int(erp_port or 2800)
    s["erp"]["user"] = erp_user or ""
    if erp_password != "":
        s["erp"]["password"] = erp_password
    s["erp"]["service"] = erp_service or "Queries/Query"
    if new_admin_password:
        s["admin_password"] = new_admin_password
    save_settings(s)
    return {"ok": True}

# ------------ Exemplo: gerar XML (usa entityID='N:[NIF]') ------------
def _hhmm_no_colon(s: str) -> str:
    return (s or "").replace(":", "")

@app.post(BASE_PREFIX + "/api/gerar_xml")
async def gerar_xml():
    # Este exemplo procura 'notas.csv' em results/ (podes adaptar ao teu fluxo real)
    notas_csv = os.path.join(RESULTS_DIR, "notas.csv")
    if not os.path.exists(notas_csv):
        raise HTTPException(status_code=404, detail="Ficheiro notas.csv não encontrado em results/")

    # agrupar por (Data, NIF, Cliente)
    groups = {}
    with open(notas_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            k = (r.get("Data",""), r.get("NIF",""), r.get("Cliente",""))
            groups.setdefault(k, []).append(r)

    created = []
    for (data, nif, cliente), items in groups.items():
        entity_id = f"N:{(nif or '').strip()}"
        fname = f"{data.replace('-','')}_S020_{nif}_{cliente}.xml"
        path = os.path.join(RESULTS_DIR, fname)
        parts = []
        parts.append("""<?xml version='1.0' encoding='windows-1252' ?>""")
        parts.append(f"<document docID='S020' entityID='{entity_id}' retID='s' status='s' trans='s'>")
        parts.append("  <docheader>")
        parts.append("    <Doc.Serie>S020</Doc.Serie>")
        parts.append(f"    <Data.Docum>{data}</Data.Docum>")
        parts.append("  </docheader>")
        parts.append("  <docitems>")
        for it in items:
            tempo = it.get("Tempo","0")
            hi = _hhmm_no_colon(it.get("HoraInicio",""))
            hf = _hhmm_no_colon(it.get("HoraFim",""))
            preco = it.get("PrecoHora","15.00")
            desc = (it.get("Descricao","") or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
            parts.append("    <rec>")
            parts.append("      <Cod.Codigo>SPICONH</Cod.Codigo>")
            parts.append(f"      <Qtd.Real>{float(tempo or '0'):.2f}</Qtd.Real>")
            parts.append(f"      <Qtd.Med1>{hi}</Qtd.Med1>")
            parts.append(f"      <Qtd.Med2>{hf}</Qtd.Med2>")
            parts.append(f"      <Val.UnBru>{float(preco or '15.00'):.2f}</Val.UnBru>")
            parts.append(f"      <Div.Obs>{desc}</Div.Obs>")
            parts.append("    </rec>")
        parts.append("  </docitems>")
        parts.append("</document>")
        xml = "\n".join(parts)
        with open(path, "w", encoding="windows-1252") as xf:
            xf.write(xml)
        created.append(fname)

    return {"ok": True, "ficheiros": created}
