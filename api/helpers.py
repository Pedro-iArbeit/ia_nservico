import csv, os, re, unicodedata
from typing import List, Dict

BASE_DIR = os.path.dirname(__file__)
CFG = os.path.join(BASE_DIR, '..', 'cfg')
DATA = os.path.join(BASE_DIR, '..', 'data')
RESULTS = os.path.join(BASE_DIR, '..', 'results')

for d in (CFG, DATA, RESULTS):
    os.makedirs(d, exist_ok=True)

CLIENTES_CSV = os.path.join(CFG, 'clientes.csv')
NOTAS_CSV = os.path.join(DATA, 'notas.csv')

def read_csv_assoc(path: str) -> List[Dict]:
    if not os.path.exists(path):
        return []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)

def write_csv_assoc(path: str, rows: List[Dict]):
    if not rows:
        rows = [{'Data':'','HoraInicio':'','HoraFim':'','Tempo':'','TempoMinutos':'','Cliente':'','NIF':'','Entidade':'','Descricao':'','PrecoHora':'','Exportado':''}][:0]
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

def append_csv_assoc(path: str, row: Dict):
    exists = os.path.exists(path)
    with open(path, 'a', newline='', encoding='utf-8') as f:
        if not exists:
            writer = csv.DictWriter(f, fieldnames=list(row.keys()))
            writer.writeheader()
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        writer.writerow(row)

def slug(s: str) -> str:
    s = unicodedata.normalize('NFKD', s)
    s = s.encode('ascii', 'ignore').decode('ascii')
    s = re.sub(r'[^A-Za-z0-9]+', '_', s)
    return s.strip('_')

def ymd(date_iso: str) -> str:
    return (date_iso or '').replace('-', '')
