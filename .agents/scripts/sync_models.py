import json
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "orca-config.json")
AGY_EXE = r"C:\Users\alswo\.gemini\bin\agy.exe"


def fetch_live_models():
    """Fetches real-time available models from Antigravity backend API via agy.exe."""
    if not os.path.exists(AGY_EXE):
        raise FileNotFoundError(f"agy.exe not found at {AGY_EXE}")

    proc = subprocess.run(
        [AGY_EXE, "models"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"agy models command failed: {proc.stderr}")

    models = {}
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("Fetching"):
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            model_id = parts[0].strip()
            display_name = parts[1].strip()
            models[model_id] = display_name
        elif len(parts) == 1:
            models[parts[0].strip()] = parts[0].strip()

    return models


def sync_config(dry_run=False):
    models = fetch_live_models()
    print(f"[API Sync] Successfully fetched {len(models)} live models from Antigravity API:")
    for mid, dname in models.items():
        print(f"  - {mid} ({dname})")

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    # Detect if Carbon is available in the account's API model list
    carbon_available = any("carbon" in mid.lower() or "carbon" in dname.lower() for mid, dname in models.items())
    print(f"\n[API Sync] Carbon access detected in current account: {carbon_available}")

    if not dry_run:
        cfg["enableCarbon"] = carbon_available
        # Merge new live models into allowedWorkerModels
        existing_allowed = set(cfg.get("allowedWorkerModels", []))
        for mid in models.keys():
            existing_allowed.add(mid)
        cfg["allowedWorkerModels"] = sorted(list(existing_allowed))

        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        print(f"[API Sync] Updated {CONFIG_PATH} with live account entitlements!")

    return models, carbon_available


if __name__ == "__main__":
    sync_config(dry_run=False)
