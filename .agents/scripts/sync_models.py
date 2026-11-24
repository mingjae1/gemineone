import datetime
import json
import os
import shutil
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "orca-config.json")
STATE_PATH = os.path.join(BASE_DIR, ".orca-state.json")

# Dynamically locate agy.exe across different user environments
def get_agy_path():
    user_home = os.environ.get("USERPROFILE", os.path.expanduser("~"))
    standard_path = os.path.join(user_home, ".gemini", "bin", "agy.exe")
    if os.path.exists(standard_path):
        return standard_path
    which_path = shutil.which("agy")
    if which_path and os.path.exists(which_path):
        return which_path
    return standard_path

AGY_EXE = get_agy_path()


def load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"[API Sync] Warning: failed to load {path}: {e}", file=sys.stderr)
    return default


def save_json(path, data):
    tmp_path = f"{path}.tmp.{os.getpid()}"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)
    except OSError as e:
        print(f"[API Sync] Error: failed to save {path}: {e}", file=sys.stderr)
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        raise


def fetch_live_models():
    """Fetches real-time available models from Antigravity backend API via agy.exe."""
    if not os.path.exists(AGY_EXE):
        raise FileNotFoundError(f"agy.exe not found at {AGY_EXE}")

    try:
        proc = subprocess.run(
            [AGY_EXE, "models"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"agy models command timed out after {e.timeout}s") from e
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

    # Detect if Carbon is available in the account's live API model list
    carbon_available = any(
        "carbon" in mid.lower() or "carbon" in dname.lower()
        for mid, dname in models.items()
    )
    print(f"\n[API Sync] Carbon access detected on local machine: {carbon_available}")

    if not dry_run:
        # 1. Update local machine state (.orca-state.json - gitignored)
        # This keeps the local environment aware of Ultra/Carbon without polluting the shared repo!
        state = load_json(STATE_PATH, {})
        state["liveModels"] = models
        state["hasCarbon"] = carbon_available
        state["lastSynced"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save_json(STATE_PATH, state)
        print(f"[API Sync] Saved local machine capabilities to gitignored .orca-state.json")

        # 2. Update shared orca-config.json
        # IMPORTANT: Keep enableCarbon safe for Pro users by default in shared config!
        cfg = load_json(CONFIG_PATH, {})
        existing_allowed = set(cfg.get("allowedWorkerModels", []))
        for mid in models.keys():
            existing_allowed.add(mid)
        cfg["allowedWorkerModels"] = sorted(list(existing_allowed))

        # Do NOT force enableCarbon=true in orca-config.json; local state handles it dynamically.
        # This guarantees that Pro users who pull this repository or install it into projects
        # will never crash from un-entitled models!
        save_json(CONFIG_PATH, cfg)
        print(f"[API Sync] Synced model pool in {CONFIG_PATH} (Safe for Pro & Ultra alike).")

    return models, carbon_available


if __name__ == "__main__":
    sync_config(dry_run=False)
