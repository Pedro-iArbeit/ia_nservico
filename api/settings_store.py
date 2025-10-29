import os, json

BASE_DIR = os.path.dirname(__file__)
CFG_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "cfg"))
os.makedirs(CFG_DIR, exist_ok=True)

SETTINGS_PATH = os.path.join(CFG_DIR, "settings.json")

DEFAULTS = {
    "admin_password": "changeme",
    "erp": {
        "host": "",
        "port": 2800,
        "user": "",
        "password": "",
        "service": "Queries/Query"
    }
}

def load_settings():
    if not os.path.exists(SETTINGS_PATH):
        save_settings(DEFAULTS)
        return DEFAULTS.copy()
    with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except Exception:
            data = {}
    out = DEFAULTS.copy()
    out["erp"] = DEFAULTS["erp"].copy()
    out.update(data or {})
    out["erp"].update((data or {}).get("erp", {}))
    return out

def save_settings(data):
    os.makedirs(CFG_DIR, exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
