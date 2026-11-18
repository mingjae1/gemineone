import datetime
import json
import os
import sys

try:
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "orca-config.json")
STATE_PATH = os.path.join(BASE_DIR, ".orca-state.json")
AUDIT_PATH = os.path.join(BASE_DIR, "orca-audit.log")

EDIT_TOOLS = {
    "edit_file",
    "write_file",
    "create_file",
    "replace_file_content",
    "multi_replace_file_content",
}


def load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default


def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def append_audit(entry):
    try:
        with open(AUDIT_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def is_exempt_path(target_path, exempt_substrings):
    if not target_path:
        return False
    norm = target_path.replace("/", "\\").lower()
    for sub in exempt_substrings:
        if sub.replace("/", "\\").lower() in norm:
            return True
    return False


def is_swarm_worker_transcript(transcript_path):
    if not transcript_path or not os.path.exists(transcript_path):
        return False
    try:
        with open(transcript_path, "r", encoding="utf-8", errors="replace") as f:
            head = f.read(8192)
        return ("[swarm] new board message" in head) or ("recorded on the board as #" in head)
    except Exception:
        return False


def resolve_worker_model(req_model, tool_args, config):
    adaptive_cfg = config.get("adaptiveEffort", {})
    tiers = config.get("tiers", {})
    allowed_models = set(config.get("allowedWorkerModels", []))
    default_tier = config.get("defaultTier", "hydrogen-high")
    fallback_model = tiers.get(default_tier, "gemini-4-hydrogen-high")

    enable_carbon = config.get("enableCarbon", False)
    carbon_fallback = config.get("carbonFallback", "gemini-4-argon-high")

    req_norm = req_model.strip().lower() if req_model else ""
    is_auto = req_norm in ("", "auto", "adaptive", "default")

    # 1. Explicit model or specific tier alias requested
    if not is_auto:
        candidate = None
        detail = None
        if req_norm in tiers:
            candidate = tiers[req_norm]
            detail = req_norm
        elif req_model in allowed_models:
            candidate = req_model
            detail = req_model

        if candidate:
            # Check if Carbon is targeted but disabled on this machine/account
            if "carbon" in candidate.lower() and not enable_carbon:
                return carbon_fallback, "carbon_fallback_disabled", f"{candidate}->{carbon_fallback}"
            return candidate, "explicit_alias" if req_norm in tiers else "explicit_allowed_model", detail

    # 2. Adaptive resolution from brief / tasks when enabled
    if adaptive_cfg.get("enabled", True):
        brief = tool_args.get("brief", "")
        tasks = tool_args.get("tasks", [])
        combined_text = (str(brief) + " " + " ".join(str(t) for t in tasks)).lower()

        rules = adaptive_cfg.get("rules", [])
        for rule in rules:
            target_model = rule.get("targetModel")
            keywords = rule.get("keywords", [])
            for kw in keywords:
                if kw.lower() in combined_text:
                    # Dynamically escalate to Carbon if enabled on deep architecture tasks
                    if rule.get("name") == "deep_architecture_concurrency" and enable_carbon:
                        return "gemini-4-carbon-high", "adaptive_carbon_escalation", f"{rule.get('name')}:{kw}"
                    return target_model, "adaptive_keyword_match", f"{rule.get('name')}:{kw}"

        adaptive_default = adaptive_cfg.get("defaultModel", fallback_model)
        return adaptive_default, "adaptive_default_fallback", None

    return fallback_model, "fallback_default", None


def main():
    raw = sys.stdin.read()
    if not raw.strip():
        print(json.dumps({"decision": "allow"}, ensure_ascii=True))
        return

    try:
        payload = json.loads(raw)
    except Exception:
        print(json.dumps({"decision": "allow"}, ensure_ascii=True))
        return

    config = load_json(CONFIG_PATH, {"enabled": False})
    if not config.get("enabled", True):
        print(json.dumps({"decision": "allow"}, ensure_ascii=True))
        return

    state = load_json(STATE_PATH, {"coordinatorConversationId": None, "workerConversations": {}})
    conv_id = payload.get("conversationId", "")
    model_name = payload.get("modelName", "")
    transcript_path = payload.get("transcriptPath", "")
    tool_call = payload.get("toolCall", {}) or {}
    tool_name = tool_call.get("name", "")
    tool_args = tool_call.get("args", {}) or {}

    workers = state.setdefault("workerConversations", {})
    is_worker = (conv_id in workers) or is_swarm_worker_transcript(transcript_path)

    if is_worker and conv_id:
        if workers.get(conv_id) != model_name:
            workers[conv_id] = model_name
            save_json(STATE_PATH, state)
    elif conv_id and state.get("coordinatorConversationId") != conv_id:
        state["coordinatorConversationId"] = conv_id
        save_json(STATE_PATH, state)

    # 1. Handle swarm tool calls (adaptive / explicit resolution)
    if tool_name == "swarm":
        action = tool_args.get("action", "")
        if action in ("add", "model"):
            req_model = tool_args.get("model")
            resolved_model, res_type, res_detail = resolve_worker_model(req_model, tool_args, config)

            out = {"decision": "allow"}
            if resolved_model != req_model:
                out["overwrite"] = {"model": resolved_model}

            append_audit({
                "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "event": "swarm_dispatch",
                "conversationId": conv_id,
                "callerModelName": model_name,
                "action": action,
                "workerName": tool_args.get("name"),
                "requestedModel": req_model,
                "resolvedModel": resolved_model,
                "resolutionType": res_type,
                "resolutionDetail": res_detail,
                "decision": "allow",
            })
            print(json.dumps(out, ensure_ascii=True))
            return

    # 2. Gate file edit tools when enforceWorkerForEdits is enabled
    if tool_name in EDIT_TOOLS and config.get("enforceWorkerForEdits", True):
        target_path = (
            tool_args.get("Path")
            or tool_args.get("TargetFile")
            or tool_args.get("file_path")
            or ""
        )
        exempt_subs = config.get("exemptPathSubstrings", [".agents", ".gemini", "brain"])
        if not is_exempt_path(target_path, exempt_subs) and not is_worker:
            reason = (
                f"[ORCA Guard] 메인 에이전트(conv={conv_id[:8]}, model={model_name})의 직접 파일 수정({tool_name} -> {target_path})이 차단되었습니다. "
                f"반드시 swarm 도구(action='add')로 워커(Gemini 계열 적응형 노력치 모델)에게 작업을 위임하세요."
            )
            append_audit({
                "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "event": "edit_blocked",
                "conversationId": conv_id,
                "callerModelName": model_name,
                "tool": tool_name,
                "path": target_path,
                "decision": "deny",
            })
            print(json.dumps({"decision": "deny", "reason": reason}, ensure_ascii=True))
            return

    append_audit({
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "event": "tool_allow",
        "role": "worker" if is_worker else "coordinator",
        "conversationId": conv_id,
        "callerModelName": model_name,
        "tool": tool_name,
        "decision": "allow",
    })
    print(json.dumps({"decision": "allow"}, ensure_ascii=True))


if __name__ == "__main__":
    main()
