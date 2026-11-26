#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gemineone GitHub Copilot Worker Bridge
Dispatches subagent tasks to GitHub Copilot CLI, captures outputs, and tracks usage.
"""

import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys


def get_copilot_binary():
    b = shutil.which("copilot") or shutil.which("copilot.cmd")
    if b:
        return b
    user_home = os.environ.get("USERPROFILE", os.path.expanduser("~"))
    local_app_data = os.environ.get("LOCALAPPDATA", os.path.join(user_home, "AppData", "Local"))
    candidates = [
        os.path.join(local_app_data, "GitHubCopilotCLI", "copilot.exe"),
        os.path.join(user_home, ".copilot", "copilot.exe"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def get_copilot_db_path():
    user_home = os.environ.get("USERPROFILE", os.path.expanduser("~"))
    return os.path.join(user_home, ".copilot", "session-store.db")


def get_latest_event_id(db_path):
    if not os.path.exists(db_path):
        return 0
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cur = conn.cursor()
        cur.execute("SELECT MAX(id) FROM assistant_usage_events;")
        row = cur.fetchone()
        conn.close()
        return row[0] or 0
    except Exception:
        return 0


def get_usage_since_event(db_path, start_event_id):
    if not os.path.exists(db_path):
        return {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0, "credits": 0.0, "models": []}
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT model, SUM(input_tokens), SUM(output_tokens), SUM(total_nano_aiu)
            FROM assistant_usage_events
            WHERE id > ?
            GROUP BY model;
            """,
            (start_event_id,)
        )
        rows = cur.fetchall()
        conn.close()

        total_inp = 0
        total_out = 0
        total_nano = 0
        models = []
        for m, inp, out, nano in rows:
            inp = inp or 0
            out = out or 0
            nano = nano or 0
            total_inp += inp
            total_out += out
            total_nano += nano
            models.append({"model": m, "inputTokens": inp, "outputTokens": out, "credits": nano / 1e9})

        return {
            "inputTokens": total_inp,
            "outputTokens": total_out,
            "totalTokens": total_inp + total_out,
            "credits": round(total_nano / 1e9, 4),
            "models": models,
        }
    except Exception:
        return {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0, "credits": 0.0, "models": []}


def run_copilot_task(task_prompt, files=None, model=None, work_dir=None, timeout=120):
    copilot_bin = get_copilot_binary()
    if not copilot_bin:
        return {
            "success": False,
            "error": "GitHub Copilot CLI ('copilot') is not installed or not in PATH.",
            "output": "",
        }

    db_path = get_copilot_db_path()
    start_id = get_latest_event_id(db_path)

    full_prompt = task_prompt
    if files:
        file_list = [f.strip() for f in files.split(",") if f.strip()]
        context_parts = []
        for fp in file_list:
            if os.path.exists(fp):
                try:
                    with open(fp, "r", encoding="utf-8", errors="replace") as f:
                        c = f.read()
                    context_parts.append(f"=== File: {fp} ===\n{c}\n")
                except Exception:
                    pass
        if context_parts:
            full_prompt = f"{''.join(context_parts)}\n\nInstructions:\n{task_prompt}"

    cmd = [copilot_bin, "-p", full_prompt, "--allow-all", "--silent"]
    if model:
        cmd.extend(["--model", model])

    if not work_dir:
        work_dir = os.getcwd()

    try:
        proc = subprocess.run(
            cmd,
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=True if sys.platform == "win32" else False,
        )
        output = (proc.stdout or "").strip()
        err_out = (proc.stderr or "").strip()

        usage = get_usage_since_event(db_path, start_id)

        return {
            "success": proc.returncode == 0,
            "returncode": proc.returncode,
            "output": output,
            "stderr": err_out,
            "usage": usage,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"Task timed out after {timeout} seconds.",
            "output": "",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "output": "",
        }


def main():
    parser = argparse.ArgumentParser(description="gemineone GitHub Copilot Subagent Bridge")
    parser.add_argument("--task", type=str, required=True, help="Task instructions for Copilot")
    parser.add_argument("--files", type=str, default=None, help="Comma-separated target or context files")
    parser.add_argument("--model", type=str, default=None, help="Specific model for Copilot to use")
    parser.add_argument("--work-dir", type=str, default=None, help="Working directory")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout in seconds")
    parser.add_argument("--json", action="store_true", help="Output JSON response")
    args = parser.parse_args()

    result = run_copilot_task(
        task_prompt=args.task,
        files=args.files,
        model=args.model,
        work_dir=args.work_dir,
        timeout=args.timeout,
    )

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["success"]:
            print(result["output"])
            u = result.get("usage", {})
            print(f"\n[Copilot Telemetry] Tokens: {u.get('totalTokens', 0):,} | AIC: {u.get('credits', 0.0)}", file=sys.stderr)
        else:
            print(f"[Copilot Error] {result.get('error') or result.get('stderr')}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
