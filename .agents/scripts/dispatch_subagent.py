#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gemineone Unified Subagent Dispatcher
Enables the Main Coordinator to dispatch tasks seamlessly to GitHub Copilot CLI,
OpenAI Codex CLI, or local Gemini Swarm without manual context transfer.
"""

import argparse
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import copilot_worker
import codex_worker


def dispatch_task(target, prompt, files=None, model=None, work_dir=None, read_only=False, timeout=180):
    """
    Dispatches a task to the specified subagent provider.
    target: 'copilot' | 'codex'
    """
    target = (target or "").lower().strip()

    if target in ("copilot", "github-copilot", "gitco"):
        res = copilot_worker.run_copilot_task(
            task_prompt=prompt,
            files=files,
            model=model,
            work_dir=work_dir,
            timeout=timeout,
        )
        res["provider"] = "copilot"
        return res

    elif target in ("codex", "openai-codex", "chatgpt"):
        res = codex_worker.run_codex_task(
            task_prompt=prompt,
            files=files,
            model=model,
            work_dir=work_dir,
            read_only=read_only,
            timeout=timeout,
        )
        res["provider"] = "codex"
        return res

    else:
        return {
            "success": False,
            "error": f"Unknown dispatch target '{target}'. Supported targets: copilot, codex.",
            "provider": target,
        }


def main():
    parser = argparse.ArgumentParser(description="Unified Subagent Dispatcher for gemineone Orchestrator.")
    parser.add_argument("--target", "-t", required=True, choices=["copilot", "codex", "gitco", "chatgpt"], help="Target AI provider.")
    parser.add_argument("--prompt", "-p", required=True, help="Task prompt or instruction.")
    parser.add_argument("--files", "-f", help="Comma-separated file paths for context injection.")
    parser.add_argument("--model", "-m", help="Model override for the target provider.")
    parser.add_argument("--read-only", action="store_true", help="Run with read-only permissions.")
    parser.add_argument("--timeout", type=int, default=180, help="Timeout in seconds.")
    parser.add_argument("--json", action="store_true", help="Output full JSON response.")

    args = parser.parse_args()

    result = dispatch_task(
        target=args.target,
        prompt=args.prompt,
        files=args.files,
        model=args.model,
        read_only=args.read_only,
        timeout=args.timeout,
    )

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result.get("success"):
            print(f"[{result.get('provider').upper()} Worker Output]:")
            print(result.get("output", ""))
            u = result.get("usage", {})
            if u:
                tot = u.get("totalTokens", 0)
                cred = u.get("credits")
                cred_str = f" ({cred} AIC)" if cred is not None else ""
                print(f"\n[Usage: {tot:,} tokens{cred_str}]")
        else:
            print(f"[{result.get('provider').upper()} Error]: {result.get('error')}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
