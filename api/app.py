from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import Optional, List, Dict, Tuple
import os, zipfile, html, csv, io, re
from datetime import datetime

from .helpers import (
    read_csv_assoc, write_csv_assoc, append_csv_assoc,
    slug, ymd, CLIENTES_CSV, NOTAS_CSV, RESULTS
)

BASE_PREFIX = "/nservico"

app = FastAPI(title="nservico API")

# CORS correto
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # troque por https://iarbeit.eu se quiser restringir
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Expor ficheiros gerados
app.mount(BASE_PREFIX + "/results", StaticFiles(directory=RESULTS), name="results")


# -------------------- UTIL --------------------
def hhmm_no_colon(h: str) -> str:         # "09:30" -> "0930"
    return (h or "").replace(":", "")

def hhmm_colonize(s: str) -> str:
    """Aceita '0930' -> '09:30', ou devolve o próprio se já tiver ':'."""
    s = (s or "").strip()
    if not s:
        return s
    if ":" in s:
        # normaliza 9:5 -> 09:05
        parts = s.split(":")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
        return s
    if re.fullmatch(r"\d{4}", s):
        return f"{s[:2]}:{s[2:]}"
    return s

def norm_row_from_external(r: Dict[str, str]) -> Dict[str, str]:
    """
    Normaliza um registo vindo de um CSV 'externo' (com cabeçalhos em PT):
    'Data','Hora de Início','Hora Final','Tempo','Tempo em Minutos','Cliente',
    'NIF do Cliente','Entidade','Descrição','Preço/hora','Exportado'
    Também aceita já no formato interno.
    """
    # chaves possíveis
    map_keys = {
        "Data": ["Data"],
        "HoraInicio": ["HoraInicio", "Hora de Início", "Hora de Inicio", "Hora Início", "Hora Inicio"],
        "HoraFim": ["HoraFim", "Hora Final", "Hora de Fim"],
        "Tempo": ["Tempo"],
        "TempoMinutos": ["TempoMinutos", "Tempo em Minutos", "Minutos"],
        "Cliente": ["Cliente"],
        "NIF": ["NIF", "NIF do Cliente", "NIF Cliente"],
        "Entidade": ["Entidade"],
        "Descricao": ["Descricao", "Descrição", "Descriçao"],
        "PrecoHora": ["PrecoHora", "Preço/hora", "Preco/hora", "Preço Hora"],
        "Exportado": ["Exportado"],
    }

    def first_key(d: Dict[str, str], keys: List[str]) -> Optional[str]:
        for k in keys:
            if k in d and d[k] is not None:
                return d[k]
        return None

    out = {}
    out["Data"] = (first_key(r, map_keys["Data"]) or "").strip()

    out["HoraInicio"] = hhmm_colonize(first_key(r, map_keys["HoraInicio"]) or "")
    out["HoraFim"] = hhmm_colonize(first_key(r, map_keys["HoraFim"]) or "")

    # Tempo (horas decimais)
    tempo_str = (first_key(r, map_keys["Tempo"]) or "").strip().replace(",", ".")
    try:
        tempo_float = float(tempo_str) if tempo_str else None
    except ValueError:
        tempo_float = None

    # Tempo em Minutos (inteiro)
    tempo_min_str = (first_key(r, map_keys["TempoMinutos"]) or "").strip()
    try:
        tempo_min = int(float(tempo_min_str)) if tempo_min_str else None
    except ValueError:
        tempo_min = None

    # se só veio minutos, calcula horas; se só veio horas, calcula minutos
    if tempo_float is None and tempo_min is not None:
        tempo_float = round(tempo_min / 60.0, 2)
    if tempo_min is None and tempo_float is not None:
        tempo_min = int(round(tempo_float * 60))

    out["Tempo"] = f"{tempo_float:.2f}" if tempo_float is not None else ""
    out["TempoMinutos"] = str(int(tempo_min)) if tempo_min is not None else ""

    out["Cliente"] = (first_key(r, map_keys["Cliente"]) or "").strip()
    out["NIF"] = (first_key(r, map_keys["NIF"]) or "").strip()
    out["Entidade"] = (first_key(r, map_keys["Entidade"]) or "").strip()
    out["Descricao"] = (first_key(r, map_keys["Descricao"]) or "").strip()

    preco_str = (first_key(r, map_keys["PrecoHora"]) or "").strip().replace(",", ".")
    try:
        preco = float(preco_str) if preco_str else 15.00
    except ValueError:
        preco = 15.00
    out["PrecoHora"] = f"{preco:.2f}"

    exportado = (first_key(r, map_keys["Exportado"]) or "").strip().lower()
    out["Exportado"] = "sim" if exportado in ("sim", "true", "1", "yes") else "não"

    return out


# -------------------- Clientes --------------------
@app.get(BASE_PREFIX + "/api/clientes")
async def get_clientes():
    return {"rows": read_csv_assoc(CLIENTES_CSV)}

@app.post(BASE_PREFIX + "/api/clientes/upload")
async def upload_clientes(file: UploadFile = File(...)):
    content = await file.read()
    with open(CLIENTES_CSV, "wb") as f:
        f.write(content)
    return {"ok": True}

@app.post(BASE_PREFIX + "/api/clientes/clear")
async def clear_clientes():
    with open(CLIENTES_CSV, "w", encoding="utf-8") as f:
        f.write("Cliente,NIF,Entidade\n")
    return {"ok": True}


# -------------------- Notas --------------------
@app.get(BASE_PREFIX + "/api/notas")
async def get_notas():
    return {"rows": read_csv_assoc(NOTAS_CSV)}

@app.post(BASE_PREFIX + "/api/notas")
async def append_nota(
    Data: str = Form(...),
    HoraInicio: str = Form(...),  # "HH:MM"
    HoraFim: str = Form(...),     # "HH:MM"
    Tempo: float = Form(...),     # horas decimais
    TempoMinutos: int = Form(...),
    Cliente: str = Form(...),
    NIF: str = Form(...),
    Entidade: Optional[str] = Form(None),
    Descricao: Optional[str] = Form(None),
    PrecoHora: float = Form(15.00),
):
    row = {
        "Data": Data,
        "HoraInicio": HoraInicio,
        "HoraFim": HoraFim,
        "Tempo": f"{float(Tempo):.2f}",
        "TempoMinutos": str(int(TempoMinutos)),
        "Cliente": Cliente,
        "NIF": NIF,
        "Entidade": (Entidade or ""),
        "Descricao": (Descricao or ""),
        "PrecoHora": f"{PrecoHora:.2f}",
        "Exportado": "não",
    }
    append_csv_assoc(NOTAS_CSV, row)
    return {"ok": True}

@app.post(BASE_PREFIX + "/api/notas/delete")
async def delete_nota(
    Data: str = Form(...),
    HoraInicio: str = Form(...),
    HoraFim: str = Form(...),
    Tempo: str = Form(...),
    TempoMinutos: str = Form(...),
    Cliente: str = Form(...),
    NIF: str = Form(...),
    Entidade: str = Form(""),
    Descricao: str = Form(""),
    PrecoHora: str = Form("15.00"),
):
    rows = read_csv_assoc(NOTAS_CSV)

    def same(a: Dict[str, str], k: str, v: str) -> bool:
        return (a.get(k, "") or "") == (v or "")

    # normaliza formatos recebidos
    Tempo = f"{float(Tempo):.2f}"
    TempoMinutos = str(int(float(TempoMinutos)))
    PrecoHora = f"{float(PrecoHora):.2f}"
    HoraInicio = hhmm_colonize(HoraInicio)
    HoraFim = hhmm_colonize(HoraFim)

    idx_to_del = -1
    for i, r in enumerate(rows):
        if all([
            same(r, "Data", Data),
            same(r, "HoraInicio", HoraInicio),
            same(r, "HoraFim", HoraFim),
            same(r, "Tempo", Tempo),
            same(r, "TempoMinutos", TempoMinutos),
            same(r, "Cliente", Cliente),
            same(r, "NIF", NIF),
            same(r, "Entidade", Entidade),
            same(r, "Descricao", Descricao),
            same(r, "PrecoHora", PrecoHora),
        ]):
            idx_to_del = i
            break

    if idx_to_del < 0:
        raise HTTPException(status_code=404, detail="Registo não encontrado para eliminar.")

    rows.pop(idx_to_del)
    write_csv_assoc(NOTAS_CSV, rows)
    return {"ok": True}

@app.post(BASE_PREFIX + "/api/notas/upload")
async def upload_notas_csv(
    file: UploadFile = File(...),
    mode: str = Form("append"),   # "append" (default) ou "replace"
):
    """
    Importa um CSV de registos.
    Aceita cabeçalhos em PT ou no formato interno.
    mode: append -> anexa; replace -> substitui por completo.
    """
    raw = await file.read()
    # tenta utf-8 / utf-8-sig
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    parsed: List[Dict[str, str]] = []
    for row in reader:
        norm = norm_row_from_external(row)
        # precisa pelo menos Data, Cliente, NIF para fazer sentido
        if (norm.get("Data") and norm.get("Cliente") and norm.get("NIF")):
            parsed.append(norm)

    if not parsed:
        raise HTTPException(status_code=400, detail="CSV sem linhas válidas.")

    if mode == "replace":
        write_csv_assoc(NOTAS_CSV, parsed)
    else:
        # append ao que existir
        current = read_csv_assoc(NOTAS_CSV)
        current.extend(parsed)
        write_csv_assoc(NOTAS_CSV, current)

    return {"ok": True, "rows": len(parsed), "mode": mode}


# -------------------- XML --------------------
def make_docs(rows: List[Dict[str, str]]) -> List[Tuple[str, str, str, str]]:
    # um documento por Cliente + NIF + Data
    groups: Dict[str, List[Dict[str, str]]] = {}
    for r in rows:
        k = f"{r.get('Cliente','')}__{r.get('NIF','')}__{r.get('Data','')}"
        groups.setdefault(k, []).append(r)

    outputs: List[Tuple[str, str, str, str]] = []
    for k, items in groups.items():
        cliente, nif, data = k.split("__")
        header = (
            "<?xml version='1.0' encoding='windows-1252' ?>\n"
            f"<document docID='S020' entityID='N:{nif}' retID='s' status='s' trans='s'>\n"
            "  <docheader>\n"
            "    <Doc.Serie>S020</Doc.Serie>\n"
            f"    <Data.Docum>{data}</Data.Docum>\n"
            "  </docheader>\n"
            "  <docitems>\n"
        )
        items_xml = "\n".join(
            [
                (
                    "    <rec>\n"
                    "      <Cod.Codigo>SPICONH</Cod.Codigo>\n"
                    f"      <Qtd.Real>{float(it.get('Tempo','0') or '0'):.2f}</Qtd.Real>\n"   # HORAS DECIMAIS
                    f"      <Qtd.Med1>{hhmm_no_colon(it.get('HoraInicio',''))}</Qtd.Med1>\n"
                    f"      <Qtd.Med2>{hhmm_no_colon(it.get('HoraFim',''))}</Qtd.Med2>\n"
                    f"      <Val.UnBru>{float(it.get('PrecoHora','15.00') or '15.00'):.2f}</Val.UnBru>\n"
                    f"      <Div.Obs>{html.escape(it.get('Descricao','') or '')}</Div.Obs>\n"
                    "    </rec>"
                )
                for it in items
            ]
        )
        footer = "\n  </docitems>\n</document>"
        outputs.append((cliente, nif, data, header + items_xml + footer))
    return outputs

@app.get(BASE_PREFIX + "/api/xml/preview")
async def preview_xml():
    rows = [r for r in read_csv_assoc(NOTAS_CSV) if r.get("Exportado", "não") != "sim"]
    outputs = make_docs(rows)
    return {"xml": "\n\n".join([doc for (_, _, _, doc) in outputs])}

@app.post(BASE_PREFIX + "/api/xml/export")
async def export_xml(limpar: bool = Form(False)):
    rows = read_csv_assoc(NOTAS_CSV)
    pend = [r for r in rows if r.get("Exportado", "não") != "sim"]
    if not pend:
        return {"file": None}

    outputs = make_docs(pend)
    generated = []
    for (cliente, nif, data, xml) in outputs:
        fname = f"{ymd(data)}_S020_{nif}_{slug(cliente)}.xml"
        with open(os.path.join(RESULTS, fname), "w", encoding="windows-1252", newline="") as f:
            f.write(xml)
        generated.append(fname)

    # limpar ou marcar como exportado
    if limpar:
        rows = [r for r in rows if r.get("Exportado", "não") == "sim"]
    else:
        for r in rows:
            if r.get("Exportado", "não") != "sim":
                r["Exportado"] = "sim"

    write_csv_assoc(NOTAS_CSV, rows)

    if len(generated) == 1:
        return {"file": f"{BASE_PREFIX}/results/{generated[0]}"}

    zipname = f"export_{datetime.now().strftime('%Y%m%d_%H%M')}.zip"
    zipabs = os.path.join(RESULTS, zipname)
    with zipfile.ZipFile(zipabs, "w", zipfile.ZIP_DEFLATED) as z:
        for g in generated:
            z.write(os.path.join(RESULTS, g), arcname=g)
    return {"file": f"{BASE_PREFIX}/results/{zipname}"}