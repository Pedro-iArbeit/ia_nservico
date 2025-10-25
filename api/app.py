from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import Optional
import os, zipfile, html
from datetime import datetime
from api.helpers import read_csv_assoc, write_csv_assoc, append_csv_assoc, slug, ymd, CLIENTES_CSV, NOTAS_CSV, RESULTS

BASE_PREFIX = "/nservico"

app = FastAPI(title='nservico API')
app.add_middleware(
    CORSMiddleware(
        allow_origins=[""],
        allow_credentials=True,
        allow_methods=[""],
        allow_headers=["*"],
    )
)

# Serve results (dev/prod)
app.mount(BASE_PREFIX + "/results", StaticFiles(directory=RESULTS), name="results")

@app.get(BASE_PREFIX + "/api/clientes")
async def get_clientes():
    return {"rows": read_csv_assoc(CLIENTES_CSV)}

@app.post(BASE_PREFIX + "/api/clientes/upload")
async def upload_clientes(file: UploadFile = File(...)):
    content = await file.read()
    with open(CLIENTES_CSV, 'wb') as f:
        f.write(content)
    return {"ok": True}

@app.post(BASE_PREFIX + "/api/clientes/clear")
async def clear_clientes():
    with open(CLIENTES_CSV, 'w', encoding='utf-8') as f:
        f.write("Cliente,NIF,Entidade\n")
    return {"ok": True}

@app.get(BASE_PREFIX + "/api/notas")
async def get_notas():
    return {"rows": read_csv_assoc(NOTAS_CSV)}

@app.post(BASE_PREFIX + "/api/notas")
async def append_nota(
    Data: str = Form(...), HoraInicio: str = Form(...), HoraFim: str = Form(...),
    Tempo: float = Form(...), TempoMinutos: int = Form(...),
    Cliente: str = Form(...), NIF: str = Form(...), Entidade: Optional[str] = Form(None),
    Descricao: Optional[str] = Form(None), PrecoHora: float = Form(15.00)
):
    row = {
        'Data': Data, 'HoraInicio': HoraInicio, 'HoraFim': HoraFim,
        'Tempo': f"{float(Tempo):.2f}", 'TempoMinutos': str(int(TempoMinutos)),
        'Cliente': Cliente, 'NIF': NIF, 'Entidade': Entidade or '',
        'Descricao': Descricao or '', 'PrecoHora': f"{PrecoHora:.2f}",
        'Exportado': 'não'
    }
    append_csv_assoc(NOTAS_CSV, row)
    return {"ok": True}

def hhmm_no_colon(h):  # "09:30" -> "0930"
    return (h or "").replace(":", "")

def make_docs(rows):
    groups = {}
    for r in rows:
        k = f"{r.get('Cliente','')}__{r.get('NIF','')}__{r.get('Data','')}"
        groups.setdefault(k, []).append(r)
    outputs = []
    for k, items in groups.items():
        cliente, nif, data = k.split('__')
        header = (
            "<?xml version='1.0' encoding='windows-1252' ?>\n"
            f"<document docID='S020' entityID='N:{nif}' retID='s' status='s' trans='s'>\n"
            "  <docheader>\n"
            "    <Doc.Serie>S020</Doc.Serie>\n"
            f"    <Data.Docum>{data}</Data.Docum>\n"
            "  </docheader>\n"
            "  <docitems>\n"
        )
        items_xml = "\n".join([
            (
                "    <rec>\n"
                "      <Cod.Codigo>SPICONH</Cod.Codigo>\n"
                f"      <Qtd.Real>{int(float(it.get('TempoMinutos','0')))}</Qtd.Real>\n"
                f"      <Qtd.Med1>{hhmm_no_colon(it.get('HoraInicio',''))}</Qtd.Med1>\n"
                f"      <Qtd.Med2>{hhmm_no_colon(it.get('HoraFim',''))}</Qtd.Med2>\n"
                f"      <Val.UnBru>{float(it.get('PrecoHora','15.00')):.2f}</Val.UnBru>\n"
                f"      <Div.Obs>{html.escape(it.get('Descricao','') or '')}</Div.Obs>\n"
                "    </rec>"
            ) for it in items
        ])
        footer = "\n  </docitems>\n</document>"
        outputs.append((cliente, nif, data, header + items_xml + footer))
    return outputs

@app.get(BASE_PREFIX + "/api/xml/preview")
async def preview_xml():
    rows = [r for r in read_csv_assoc(NOTAS_CSV) if r.get('Exportado','não')!='sim']
    outputs = make_docs(rows)
    return {"xml": "\n\n".join([doc for (_,_,_,doc) in outputs])}

@app.post(BASE_PREFIX + "/api/xml/export")
async def export_xml(limpar: bool = Form(False)):
    rows = read_csv_assoc(NOTAS_CSV)
    pend = [r for r in rows if r.get('Exportado','não')!='sim']
    if not pend:
        return {"file": None}
    outputs = make_docs(pend)
    generated = []
    for (cliente, nif, data, xml) in outputs:
        fname = f"{ymd(data)}_S020_{nif}_{slug(cliente)}.xml"
        with open(os.path.join(RESULTS, fname), 'w', encoding='windows-1252', newline='') as f:
            f.write(xml)
        generated.append(fname)
    if limpar:
        rows = [r for r in rows if r.get('Exportado','não')=='sim']
    else:
        for r in rows:
            if r.get('Exportado','não')!='sim':
                r['Exportado'] = 'sim'
    write_csv_assoc(NOTAS_CSV, rows)
    if len(generated)==1:
        return {"file": f"{BASE_PREFIX}/results/{generated[0]}"}
    zipname = f"export_{datetime.now().strftime('%Y%m%d_%H%M')}.zip"
    zipabs = os.path.join(RESULTS, zipname)
    with zipfile.ZipFile(zipabs, 'w', zipfile.ZIP_DEFLATED) as z:
        for g in generated:
            z.write(os.path.join(RESULTS, g), arcname=g)
    return {"file": f"{BASE_PREFIX}/results/{zipname}"}
