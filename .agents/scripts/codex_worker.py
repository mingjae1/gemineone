#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gemineone OpenAI Codex Worker Bridge
Dispatches subagent tasks to OpenAI Codex CLI, captures outputs, and tracks usage.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys


def get_codex_binary():
    b = shutil.which("codex") or shutil.which("codex.cmd")
    if b:
        return b
    user_home = os.environ.get("USERPROFILE", os.path.expanduser("~"))
    local_app_data = os.environ.get("LOCALAPPDATA", os.path.join(user_home, "AppData", "Local"))
    candidates = [
        os.path.join(local_app_data, "Programs", "OpenAI", "Codex", "bin", "codex.exe"),
        os.path.join(user_home, ".codex", "codex.exe"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def parse_codex_jsonl_output(stdout_text):
    """
    Parses JSONL output from `codex exec --json`.
    Extracts agent messages, thread_id, and cumulative token usage.
    """
    thread_id = None
    agent_messages = []
    total_input = 0
    total_output = 0
    total_cached = 0
    total_reasoning = 0
    errors = []

    for line in stdout_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except Exception:
            continue

        ev_type = ev.get("type")

        if ev_type == "thread.started":
            thread_id = ev.get("thread_id")

        elif ev_type == "item.completed":
            item = ev.get("item", {})
            if item.get("type") == "agent_message":
                text = item.get("text", "")
                if text:
                    agent_messages.append(text)
            elif item.get("type") == "error":
                errors.append(item.get("message", "Unknown item error"))

        elif ev_type == "turn.completed":
            usage = ev.get("usage", {})
            total_input += usage.get("input_tokens", 0) or 0
            total_output += usage.get("output_tokens", 0) or 0
            total_cached += usage.get("cached_input_tokens", 0) or 0
            total_reasoning += usage.get("reasoning_output_tokens", 0) or 0

        elif ev_type == "error":
            errors.append(ev.get("message", "Codex execution error"))

    final_output = "\n\n".join(agent_messages).strip()

    return {
        "thread_id": thread_id,
        "output": final_output,
        "errors": errors,
        "usage": {
            "inputTokens": total_input,
            "outputTokens": total_output,
            "cachedTokens": total_cached,
            "reasoningTokens": total_reasoning,
            "totalTokens": total_input + total_output,
        },
    }


def run_codex_task(task_prompt, files=None, model=None, work_dir=None, read_only=False, timeout=180):
    codex_bin = get_codex_binary()
    if not codex_bin:
        return {
            "success": False,
            "error": "OpenAI Codex CLI ('codex') is not installed or not in PATH.",
            "output": "",
        }

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

    cmd = [codex_bin, "exec", full_prompt, "--json"]
    if read_only:
        cmd.extend(["--sandbox", "read-only"])
    else:
        cmd.append("--approve-for-me")

    if model:
        cmd.extend(["-m", model])

    if not work_dir:
        work_dir = os.getcwd()
    cmd.extend(["-C", work_dir])

    try:
        proc = subprocess.run(
            cmd,
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
            shell=True if sys.platform == "win32" else False,
        )

        parsed = parse_codex_jsonl_output(proc.stdout or "")

        # Fallback if no agent message parsed but stdout has text
        output = parsed["output"]
        if not output and proc.returncode == 0:
            output = (proc.stdout or "").strip()

        err_out = (proc.stderr or "").strip()
        # Filter benign stderr notice
        err_lines = [l for l in err_out.splitlines() if "Reading additional input from stdin..." not in l]
        cleaned_stderr = "\n".join(err_lines).strip()

        is_success = (proc.returncode == 0) and not parsed["errors"]

        return {
            "success": is_success,
            "returncode": proc.returncode,
            "output": output,
            "stderr": cleaned_stderr,
            "thread_id": parsed["thread_id"],
            "usage": parsed["usage"],
            "errors": parsed["errors"],
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
    parser = argparse.ArgumentParser(description="Run a subagent task via OpenAI Codex CLI.")
    parser.add_argument("-p", "--prompt", required=True, help="Task prompt or instruction.")
    parser.add_argument("-f", "--files", help="Comma-separated file paths to include as context.")
    parser.add_argument("-m", "--model", help="Model override (e.g. gpt-5.4, o3).")
    parser.add_argument("-C", "--dir", help="Working directory for Codex execution.")
    parser.add_argument("--read-only", action="store_true", help="Run with read-only sandbox.")
    parser.add_argument("--timeout", type=int, default=180, help="Execution timeout in seconds.")
    parser.add_argument("--json", action="store_true", help="Output result as JSON.")

    args = parser.parse_args()

    result = run_codex_task(
        task_prompt=args.prompt,
        files=args.files,
        model=args.model,
        work_dir=args.dir,
        read_only=args.read_only,
        timeout=args.timeout,
    )

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result.get("success"):
            print(result.get("output", ""))
            u = result.get("usage", {})
            if u.get("totalTokens"):
                print(f"\n[Codex Usage: {u.get('totalTokens'):,} tokens (In: {u.get('inputTokens'):,}, Out: {u.get('outputTokens'):,})]")
        else:
            print(f"Error: {result.get('error') or result.get('errors')}", file=sys.stderr)
            if result.get("stderr"):
                print(result["stderr"], file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
