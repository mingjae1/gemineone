import argparse
import datetime
import json
import os
import pathlib
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "orca-config.json")
STATE_PATH = os.path.join(BASE_DIR, ".orca-state.json")


def load_json(path, default=None):
    if default is None:
        default = {}
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default


def save_json(path, data):
    tmp_path = f"{path}.tmp.{os.getpid()}"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        import time
        replaced = False
        for attempt in range(5):
            try:
                os.replace(tmp_path, path)
                replaced = True
                break
            except PermissionError:
                time.sleep(0.05 * (attempt + 1))
        if not replaced:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            try:
                os.remove(tmp_path)
            except OSError:
                pass
    except Exception as e:
        print(f"[Quota Meter] Error saving {path}: {e}", file=sys.stderr)
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        raise


def get_default_brain_dir():
    user_home = os.environ.get("USERPROFILE", os.path.expanduser("~"))
    return os.path.join(user_home, ".gemini", "antigravity", "brain")


def get_default_daemon_dir():
    user_home = os.environ.get("USERPROFILE", os.path.expanduser("~"))
    return os.path.join(user_home, ".gemini", "antigravity", "daemon")


def fetch_live_antigravity_quota(daemon_dir=None, timeout=2):
    """Directly queries the active Antigravity Hub Language Server via Connect RPC.

    Returns a dict with live remaining quota percentages and reset times,
    or None if the daemon is offline or unreachable.
    """
    if not daemon_dir:
        daemon_dir = get_default_daemon_dir()
    if not os.path.exists(daemon_dir):
        return None

    import glob
    import urllib.request

    hub_files = sorted(
        glob.glob(os.path.join(daemon_dir, "hub_*.json")),
        key=lambda f: os.path.getmtime(f) if os.path.exists(f) else 0,
        reverse=True,
    )
    if not hub_files:
        return None

    for hf in hub_files:
        try:
            with open(hf, "r", encoding="utf-8") as f:
                data = json.load(f)
            port = data.get("httpPort")
            csrf = data.get("csrfToken")
            if not port or not csrf:
                continue

            url = f"http://127.0.0.1:{port}/exa.language_server_pb.LanguageServerService/RetrieveUserQuotaSummary"
            req = urllib.request.Request(
                url,
                data=b"{}",
                headers={
                    "Content-Type": "application/json",
                    "x-codeium-csrf-token": csrf,
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    res_json = json.loads(resp.read().decode("utf-8"))
                    groups = res_json.get("response", {}).get("groups", [])
                    result = {
                        "source": "live_hub_api",
                        "fiveHourRemainingPercent": None,
                        "weeklyRemainingPercent": None,
                        "reset5h": None,
                        "resetWeekly": None,
                        "desc5h": None,
                        "descWeekly": None,
                        "claudeGptWeeklyPercent": None,
                        "claudeGpt5hPercent": None,
                    }
                    for g in groups:
                        disp = g.get("displayName", "")
                        buckets = g.get("buckets", [])
                        if "Gemini" in disp:
                            for b in buckets:
                                win = b.get("window", "")
                                bid = b.get("bucketId", "")
                                frac = b.get("remainingFraction", 1.0)
                                pct = round(frac * 100.0, 1)
                                if win == "5h" or "5h" in bid:
                                    result["fiveHourRemainingPercent"] = pct
                                    result["reset5h"] = b.get("resetTime")
                                    result["desc5h"] = b.get("description")
                                elif win == "weekly" or "weekly" in bid:
                                    result["weeklyRemainingPercent"] = pct
                                    result["resetWeekly"] = b.get("resetTime")
                                    result["descWeekly"] = b.get("description")
                        elif "Claude" in disp or "GPT" in disp:
                            for b in buckets:
                                win = b.get("window", "")
                                bid = b.get("bucketId", "")
                                frac = b.get("remainingFraction", 1.0)
                                pct = round(frac * 100.0, 1)
                                if win == "weekly" or "weekly" in bid:
                                    result["claudeGptWeeklyPercent"] = pct
                                    result["reset3pWeekly"] = b.get("resetTime")
                                elif win == "5h" or "5h" in bid:
                                    result["claudeGpt5hPercent"] = pct
                                    result["reset3p5h"] = b.get("resetTime")

                    if result["fiveHourRemainingPercent"] is not None and result["weeklyRemainingPercent"] is not None:
                        return result
        except Exception:
            continue
    return None


def find_latest_conversation_id(brain_dir=None):
    if not brain_dir:
        brain_dir = get_default_brain_dir()
    if not os.path.exists(brain_dir):
        return None
    latest_id = None
    latest_mtime = 0.0
    for p in pathlib.Path(brain_dir).glob("*/.system_generated/logs/transcript.jsonl"):
        try:
            m = p.stat().st_mtime
            if m > latest_mtime:
                latest_mtime = m
                latest_id = p.parent.parent.parent.name
        except Exception:
            pass
    return latest_id


def compute_conversation_tokens(conv_id, brain_dir=None):
    if not conv_id:
        return 0
    if not brain_dir:
        brain_dir = get_default_brain_dir()
    transcript_path = os.path.join(brain_dir, conv_id, ".system_generated", "logs", "transcript.jsonl")
    if not os.path.exists(transcript_path):
        return 0

    total = 0
    try:
        with open(transcript_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    d = json.loads(line)
                    inp = d.get("input_tokens", 0) or 0
                    out = d.get("output_tokens", 0) or 0
                    total += (inp + out)
                except Exception:
                    pass
    except Exception:
        pass
    return total


def get_default_db_path():
    user_home = os.environ.get("USERPROFILE", os.path.expanduser("~"))
    return os.path.join(user_home, ".gemini", "antigravity", "conversation_summaries.db")


def get_agent_breakdown(conv_id, brain_dir=None, db_path=None):
    if not conv_id:
        return []
    if not brain_dir:
        brain_dir = get_default_brain_dir()
    if not db_path:
        db_path = get_default_db_path()

    state = load_json(STATE_PATH, {})
    worker_models = state.get("workerConversations", {})

    breakdown = []
    coord_tokens = compute_conversation_tokens(conv_id, brain_dir)
    breakdown.append({
        "name": "coordinator",
        "conversationId": conv_id,
        "tokens": coord_tokens,
        "model": "gemini-3.8-flash-high",
        "isCoordinator": True,
    })

    if not os.path.exists(db_path):
        return breakdown

    try:
        import sqlite3
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cur = conn.cursor()
        cur.execute(
            "SELECT conversation_id, agent_name FROM conversation_summaries WHERE parent_conversation_id = ?;",
            (conv_id,),
        )
        rows = cur.fetchall()
        conn.close()

        for wid, wname in rows:
            wtokens = compute_conversation_tokens(wid, brain_dir)
            wmodel = worker_models.get(wid, "adaptive-worker")
            breakdown.append({
                "name": wname or "worker",
                "conversationId": wid,
                "tokens": wtokens,
                "model": wmodel,
                "isCoordinator": False,
            })
    except Exception:
        pass

    return breakdown


def get_external_providers():
    providers = {}
    import shutil
    import subprocess

    user_home = os.environ.get("USERPROFILE", os.path.expanduser("~"))
    local_app_data = os.environ.get("LOCALAPPDATA", os.path.join(user_home, "AppData", "Local"))
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")

    def resolve_cli(name, candidates):
        b = shutil.which(name) or shutil.which(f"{name}.cmd") or shutil.which(f"{name}.exe")
        if b:
            return b
        for c in candidates:
            if os.path.exists(c):
                return c
        return None

    # 1. Claude Code CLI
    claude_bin = resolve_cli("claude", [
        os.path.join(user_home, ".local", "bin", "claude.exe"),
        os.path.join(local_app_data, "Programs", "claude", "claude.exe"),
    ])
    claude_stats = os.path.join(user_home, ".claude", "stats-cache.json")
    claude_total_msg = 0
    claude_total_tools = 0
    claude_days = 0
    if os.path.exists(claude_stats):
        try:
            with open(claude_stats, "r", encoding="utf-8") as f:
                cs = json.load(f)
                daily = cs.get("dailyActivity", [])
                claude_total_msg = sum(d.get("messageCount", 0) for d in daily)
                claude_total_tools = sum(d.get("toolCallCount", 0) for d in daily)
                claude_days = len(daily)
        except Exception:
            pass

    if claude_bin:
        providers["claude"] = {
            "installed": True,
            "loggedIn": False,
            "version": "2.1.332",
            "totalMessages": claude_total_msg,
            "totalToolCalls": claude_total_tools,
            "daysTracked": claude_days,
            "status": "설치됨 (로그인 대기: claude auth login)",
        }
    else:
        providers["claude"] = {"installed": False}

    # 2. OpenAI Codex CLI
    codex_bin = resolve_cli("codex", [
        os.path.join(local_app_data, "Programs", "OpenAI", "Codex", "bin", "codex.exe"),
        os.path.join(user_home, ".codex", "codex.exe"),
    ])
    codex_auth = os.path.join(user_home, ".codex", "auth.json")
    codex_cfg = os.path.join(user_home, ".codex", "config.toml")
    codex_info = {
        "installed": bool(codex_bin),
        "loggedIn": False,
        "authMode": None,
        "email": None,
        "plan": None,
        "model": "gpt-6-luna",
        "reasoningEffort": "medium",
    }
    if os.path.exists(codex_auth):
        try:
            import base64
            with open(codex_auth, "r", encoding="utf-8") as f:
                d = json.load(f)
                codex_info["authMode"] = d.get("auth_mode")
                codex_info["loggedIn"] = bool(d.get("auth_mode"))
                token = d.get("tokens", {}).get("id_token", "")
                if token and "." in token:
                    parts = token.split(".")
                    if len(parts) >= 2:
                        padding = 4 - (len(parts[1]) % 4)
                        payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=" * (padding % 4)).decode("utf-8"))
                        codex_info["email"] = payload.get("email")
                        auth_meta = payload.get("https://api.openai.com/auth", {})
                        codex_info["plan"] = auth_meta.get("chatgpt_plan_type", "free")
                        codex_info["subscriptionUntil"] = auth_meta.get("chatgpt_subscription_active_until")
        except Exception:
            pass

    if os.path.exists(codex_cfg):
        try:
            with open(codex_cfg, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("model ="):
                        codex_info["model"] = line.split("=")[1].strip().strip('"').strip("'")
                    elif line.strip().startswith("model_reasoning_effort ="):
                        codex_info["reasoningEffort"] = line.split("=")[1].strip().strip('"').strip("'")
        except Exception:
            pass
    providers["codex"] = codex_info

    # 3. GitHub Copilot CLI
    copilot_bin = resolve_cli("copilot", [
        os.path.join(local_app_data, "GitHubCopilotCLI", "copilot.exe"),
        os.path.join(user_home, ".copilot", "copilot.exe"),
    ])
    if copilot_bin:
        copilot_dir = os.path.join(user_home, ".copilot")
        cfg_path = os.path.join(copilot_dir, "config.json")
        db_path = os.path.join(copilot_dir, "session-store.db")
        cp_user = None
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    content = "".join(l for l in f if not l.strip().startswith("//"))
                    d = json.loads(content)
                    cp_user = d.get("lastLoggedInUser", {}).get("login")
            except Exception:
                pass

        cp_tokens = 0
        cp_credits = 0.0
        if os.path.exists(db_path):
            try:
                import sqlite3
                conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
                cur = conn.cursor()
                cur.execute("SELECT SUM(input_tokens + output_tokens), SUM(total_nano_aiu) FROM assistant_usage_events;")
                row = cur.fetchone()
                conn.close()
                if row and row[0]:
                    cp_tokens = int(row[0])
                    cp_credits = round((row[1] or 0) / 1e9, 3)
            except Exception:
                pass

        providers["copilot"] = {
            "installed": True,
            "loggedIn": bool(cp_user),
            "user": cp_user or "unknown",
            "tokens": cp_tokens,
            "credits": cp_credits,
            "version": "1.0.115",
        }
    else:
        providers["copilot"] = {"installed": False}

    # 4. GitHub CLI (gh)
    gh_bin = resolve_cli("gh", [
        os.path.join(program_files, "GitHub CLI", "gh.exe"),
        os.path.join(local_app_data, "Microsoft", "WinGet", "Links", "gh.exe"),
    ])
    gh_logged_in = False
    gh_user = None
    gh_rate_info = {}
    if gh_bin:
        try:
            r = subprocess.run([gh_bin, "auth", "status"], capture_output=True, text=True, timeout=2)
            out = (r.stdout + r.stderr)
            if "Logged in to" in out or "✓" in out:
                gh_logged_in = True
                import re
                m = re.search(r"account\s+([A-Za-z0-9_-]+)", out)
                if m:
                    gh_user = m.group(1)
        except Exception:
            pass

        try:
            r_rate = subprocess.run([gh_bin, "api", "rate_limit"], capture_output=True, text=True, timeout=2)
            if r_rate.returncode == 0:
                res = json.loads(r_rate.stdout).get("resources", {})
                gh_rate_info = {
                    "coreRemaining": res.get("core", {}).get("remaining"),
                    "coreLimit": res.get("core", {}).get("limit"),
                    "copilotRemaining": res.get("copilot_usage_records", {}).get("remaining"),
                    "graphqlRemaining": res.get("graphql", {}).get("remaining"),
                }
        except Exception:
            pass

    providers["gh"] = {
        "installed": bool(gh_bin),
        "loggedIn": gh_logged_in,
        "user": gh_user,
        "rateLimit": gh_rate_info,
    }

    return providers


def compute_5h_rolling_tokens(brain_dir=None, now_utc=None):
    if not brain_dir:
        brain_dir = get_default_brain_dir()
    if not os.path.exists(brain_dir):
        return 0, 0

    if now_utc is None:
        now_utc = datetime.datetime.now(datetime.timezone.utc)
    five_hours_ago = now_utc - datetime.timedelta(hours=5)

    total_tokens = 0
    total_steps = 0

    try:
        brain_path = pathlib.Path(brain_dir)
        for p in brain_path.glob("*/.system_generated/logs/transcript.jsonl"):
            try:
                mtime = datetime.datetime.fromtimestamp(p.stat().st_mtime, datetime.timezone.utc)
                if mtime < five_hours_ago:
                    continue
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            d = json.loads(line)
                            ts_str = d.get("created_at")
                            if ts_str:
                                ts = datetime.datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                                if ts < five_hours_ago:
                                    continue
                            inp = d.get("input_tokens", 0) or 0
                            out = d.get("output_tokens", 0) or 0
                            if inp or out:
                                total_tokens += (inp + out)
                                total_steps += 1
                        except Exception:
                            pass
            except Exception:
                continue
    except Exception:
        pass

    return total_tokens, total_steps


def compute_today_tokens(brain_dir=None, target_date=None):
    if not brain_dir:
        brain_dir = get_default_brain_dir()
    if not os.path.exists(brain_dir):
        return 0, 0

    if target_date is None:
        target_date = datetime.datetime.now(datetime.timezone.utc).date()

    total_tokens = 0
    total_steps = 0

    try:
        brain_path = pathlib.Path(brain_dir)
        for p in brain_path.glob("*/.system_generated/logs/transcript.jsonl"):
            try:
                mtime = datetime.datetime.fromtimestamp(p.stat().st_mtime, datetime.timezone.utc).date()
                if mtime < target_date:
                    continue
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            d = json.loads(line)
                            ts_str = d.get("created_at")
                            if ts_str:
                                ts = datetime.datetime.fromisoformat(ts_str.replace("Z", "+00:00")).date()
                                if ts != target_date:
                                    continue
                            inp = d.get("input_tokens", 0) or 0
                            out = d.get("output_tokens", 0) or 0
                            if inp or out:
                                total_tokens += (inp + out)
                                total_steps += 1
                        except Exception:
                            pass
            except Exception:
                continue
    except Exception:
        pass

    return total_tokens, total_steps


def get_dual_quota_telemetry(conv_id=None, brain_dir=None, now_utc=None, five_h_override=None, weekly_override=None, daemon_dir=None, tier=None):
    config = load_json(CONFIG_PATH, {})
    state = load_json(STATE_PATH, {})

    quota_cfg = config.get("quotaMonitoring", {})
    thresholds = quota_cfg.get("thresholds", {})
    alert_settings = quota_cfg.get("alertSettings", {})

    ag_settings = alert_settings.get("agents", {})
    th_5h = float(ag_settings.get("antigravity_5h", {}).get("threshold", alert_settings.get("fiveHourThresholdPercent", alert_settings.get("thresholdPercent", thresholds.get("fiveHourLimitPercent", quota_cfg.get("lowQuotaThresholdPercent", 70))))))
    th_weekly = float(ag_settings.get("antigravity_weekly", {}).get("threshold", alert_settings.get("weeklyThresholdPercent", alert_settings.get("thresholdPercent", thresholds.get("weeklyLimitPercent", quota_cfg.get("lowQuotaThresholdPercent", 70))))))
    th_claude = float(ag_settings.get("claude_3p", {}).get("threshold", 20.0))
    alert_scope = alert_settings.get("alertScope", "all")
    show_agent_breakdown = alert_settings.get("showAgentBreakdown", False)

    calibrated = quota_cfg.get("calibratedLimits", {})
    base_5h = calibrated.get("fiveHourRemainingPercent", 72.0)
    base_weekly = calibrated.get("weeklyRemainingPercent", 93.0)

    live_quota = None
    quota_source = "calibrated_fallback"

    # Only fetch live quota if overrides are not explicitly provided
    if five_h_override is None and weekly_override is None:
        live_quota = fetch_live_antigravity_quota(daemon_dir=daemon_dir)

    if five_h_override is not None:
        rem_5h = float(five_h_override)
        quota_source = "manual_override"
    elif live_quota and live_quota.get("fiveHourRemainingPercent") is not None:
        rem_5h = float(live_quota["fiveHourRemainingPercent"])
        quota_source = "live_hub_api"
    else:
        rem_5h = float(base_5h)

    if weekly_override is not None:
        rem_weekly = float(weekly_override)
        if quota_source != "manual_override":
            quota_source = "manual_override"
    elif live_quota and live_quota.get("weeklyRemainingPercent") is not None:
        rem_weekly = float(live_quota["weeklyRemainingPercent"])
    else:
        rem_weekly = float(base_weekly)

    # If fetched from live hub API, sync to calibratedLimits for offline resilience
    if quota_source == "live_hub_api":
        calibrated["fiveHourRemainingPercent"] = rem_5h
        calibrated["weeklyRemainingPercent"] = rem_weekly
        try:
            save_json(CONFIG_PATH, config)
        except Exception:
            pass

    if not conv_id:
        conv_id = find_latest_conversation_id(brain_dir) or state.get("coordinatorConversationId")

    session_tokens = compute_conversation_tokens(conv_id, brain_dir)
    tokens_5h, steps_5h = compute_5h_rolling_tokens(brain_dir, now_utc)

    is_low_5h = rem_5h <= th_5h
    is_low_weekly = rem_weekly <= th_weekly
    is_low_quota = is_low_5h or is_low_weekly

    # Alert scope filtering
    alert_triggered = is_low_quota
    if is_low_quota and alert_scope == "low_only" and tier:
        tier_str = str(tier).lower()
        if "low" not in tier_str:
            alert_triggered = False

    # Check if Claude 3P quota is also low
    c_3p = live_quota.get("claudeGptWeeklyPercent") if live_quota else None
    is_low_claude = (c_3p is not None and c_3p <= th_claude)
    is_low_quota = is_low_5h or is_low_weekly or is_low_claude

    recommendation = None
    if is_low_5h and is_low_weekly:
        recommendation = (
            f"5h Limit({rem_5h:.1f}%)과 Weekly Limit({rem_weekly:.1f}%)이 모두 기준치({th_5h:.1f}%) 이하입니다. "
            "즉시 gemini-4-neon-low(경량) 또는 0쿼터 모델로 전환하여 사용량을 보존하세요."
        )
    elif is_low_5h:
        recommendation = (
            f"5h Limit({rem_5h:.1f}%)이 기준({th_5h:.1f}% 이하)에 도달했습니다. "
            "슬라이딩 윈도우 회복 전까지 1~2시간 동안 경량 모델(gemini-4-neon-low) 사용을 권장합니다."
        )
    elif is_low_weekly:
        recommendation = (
            f"Weekly Limit({rem_weekly:.1f}%)이 기준({th_weekly:.1f}% 이하)에 도달했습니다. "
            "이번 주 남은 일정을 위해 Carbon/Argon 고사양 모델 호출을 자제하고 표준 티어를 권장합니다."
        )

    res = {
        "conversationId": conv_id,
        "sessionTokens": session_tokens,
        "tokens5h": tokens_5h,
        "steps5h": steps_5h,
        "fiveHourRemainingPercent": rem_5h,
        "fiveHourThreshold": th_5h,
        "isLow5h": is_low_5h,
        "weeklyRemainingPercent": rem_weekly,
        "weeklyThreshold": th_weekly,
        "isLowWeekly": is_low_weekly,
        "isLowQuota": is_low_quota,
        "alertScope": alert_scope,
        "showAgentBreakdown": show_agent_breakdown,
        "alertTriggered": alert_triggered,
        "hasCarbon": True,
        "recommendation": recommendation,
        "quotaSource": quota_source,
        "agentBreakdown": get_agent_breakdown(conv_id, brain_dir),
        "externalProviders": get_external_providers(),
    }

    if live_quota:
        res["reset5h"] = live_quota.get("reset5h")
        res["resetWeekly"] = live_quota.get("resetWeekly")
        res["reset5hLocal"] = format_local_time(live_quota.get("reset5h"))
        res["resetWeeklyLocal"] = format_local_time(live_quota.get("resetWeekly"))
        res["desc5h"] = live_quota.get("desc5h")
        res["descWeekly"] = live_quota.get("descWeekly")
        res["claudeGptWeeklyPercent"] = live_quota.get("claudeGptWeeklyPercent")
        res["claudeGpt5hPercent"] = live_quota.get("claudeGpt5hPercent")

    return res


def format_local_time(iso_utc_str):
    if not iso_utc_str:
        return ""
    try:
        dt = datetime.datetime.fromisoformat(iso_utc_str.replace("Z", "+00:00")).astimezone()
        now = datetime.datetime.now(dt.tzinfo)
        if dt.date() == now.date():
            return f"오늘 {dt.strftime('%H:%M')}"
        elif dt.date() == (now + datetime.timedelta(days=1)).date():
            return f"내일 {dt.strftime('%H:%M')}"
        else:
            return dt.strftime("%m/%d %H:%M")
    except Exception:
        return iso_utc_str


def make_bar(percent, total_blocks=15):
    filled = min(total_blocks, max(0, int(round((percent / 100.0) * total_blocks))))
    empty = total_blocks - filled
    return "█" * filled + "░" * empty


def format_markdown_footer(telemetry):
    p_5h = telemetry["fiveHourRemainingPercent"]
    p_w = telemetry["weeklyRemainingPercent"]

    reset_5h_str = format_local_time(telemetry.get("reset5h"))
    reset_w_str = format_local_time(telemetry.get("resetWeekly"))

    reset_parts = []
    if reset_5h_str:
        reset_parts.append(f"5시간 리셋: {reset_5h_str}")
    if reset_w_str:
        reset_parts.append(f"주간 리셋: {reset_w_str}")
    reset_info = f" ({' · '.join(reset_parts)})" if reset_parts else ""

    lines = [
        "---",
        "> [!NOTE] **쿼터 현황**",
        f"> • **Antigravity** : 5시간 한도 **{p_5h:.1f}%** · 주간 한도 **{p_w:.1f}%**{reset_info}",
    ]

    # 오직 실제 측정 가능한 잔여 쿼터 수치만 표시
    c_3p = telemetry.get("claudeGptWeeklyPercent")
    if c_3p is not None:
        lines.append(f"> • **Claude / 3P**  : 주간 쿼터 **{c_3p:.1f}%**")

    if telemetry.get("showAgentBreakdown", False):
        agents = telemetry.get("agentBreakdown", [])
        if len(agents) > 1:
            def fmt_t(n):
                if n >= 1_000_000:
                    return f"{n/1_000_000:.1f}M"
                elif n >= 1_000:
                    return f"{n/1_000:.1f}K"
                return str(n)

            agent_items = [f"{a['name']} ({fmt_t(a['tokens'])})" for a in agents]
            lines.append(f"> • **에이전트별**    : {' · '.join(agent_items)}")

    if telemetry.get("alertTriggered", False):
        scope_badge = " [low_only 모드]" if telemetry.get("alertScope") == "low_only" else ""
        lines.append(f"> • ⚠️ **쿼터 주의 (5시간 한도: {p_5h:.1f}%, 주간 한도: {p_w:.1f}%){scope_badge}**: {telemetry['recommendation']}")

    return "\n".join(lines)


def set_thresholds(th_all=None, th_5h=None, th_w=None, scope=None, show_breakdown=None, ag_5h=None, ag_weekly=None, claude=None, copilot=None, codex=None):
    config = load_json(CONFIG_PATH, {})
    q = config.setdefault("quotaMonitoring", {})
    t = q.setdefault("thresholds", {})
    a = q.setdefault("alertSettings", {})
    ag_dict = a.setdefault("agents", {})

    if th_all is not None:
        val = float(th_all)
        t["fiveHourLimitPercent"] = val
        t["weeklyLimitPercent"] = val
        q["lowQuotaThresholdPercent"] = val
        a["thresholdPercent"] = val
        a["fiveHourThresholdPercent"] = val
        a["weeklyThresholdPercent"] = val
        ag_dict.setdefault("antigravity_5h", {})["threshold"] = val
        ag_dict.setdefault("antigravity_weekly", {})["threshold"] = val

    if th_5h is not None or ag_5h is not None:
        val_5h = float(ag_5h if ag_5h is not None else th_5h)
        t["fiveHourLimitPercent"] = val_5h
        a["fiveHourThresholdPercent"] = val_5h
        ag_dict.setdefault("antigravity_5h", {})["threshold"] = val_5h

    if th_w is not None or ag_weekly is not None:
        val_w = float(ag_weekly if ag_weekly is not None else th_w)
        t["weeklyLimitPercent"] = val_w
        a["weeklyThresholdPercent"] = val_w
        ag_dict.setdefault("antigravity_weekly", {})["threshold"] = val_w

    if claude is not None:
        val_c = float(claude)
        ag_dict.setdefault("claude_3p", {})["threshold"] = val_c

    if copilot is not None:
        val_cp = float(copilot)
        ag_dict.setdefault("copilot", {})["threshold"] = val_cp

    if codex is not None:
        val_cdx = float(codex)
        ag_dict.setdefault("codex", {})["threshold"] = val_cdx

    if scope is not None:
        a["alertScope"] = scope
    if show_breakdown is not None:
        a["showAgentBreakdown"] = (str(show_breakdown).lower() == "true")

    save_json(CONFIG_PATH, config)


def set_calibrated_limits(rem_5h=None, rem_weekly=None):
    config = load_json(CONFIG_PATH, {})
    q = config.setdefault("quotaMonitoring", {})
    c = q.setdefault("calibratedLimits", {})

    if rem_5h is not None:
        c["fiveHourRemainingPercent"] = float(rem_5h)
    if rem_weekly is not None:
        c["weeklyRemainingPercent"] = float(rem_weekly)

    save_json(CONFIG_PATH, config)


def main():
    parser = argparse.ArgumentParser(description="Antigravity Dual Quota Meter (5h & Weekly)")
    parser.add_argument("--json", action="store_true", help="Output telemetry as JSON")
    parser.add_argument("--markdown", action="store_true", help="Output telemetry as Markdown footer")
    parser.add_argument("--conv-id", type=str, default=None, help="Conversation ID to inspect")
    parser.add_argument("--set-threshold", type=float, default=None, help="Set alert threshold (0-100) for both 5h and Weekly")
    parser.add_argument("--set-5h-threshold", type=float, default=None, help="Set 5h threshold (0-100)")
    parser.add_argument("--set-weekly-threshold", type=float, default=None, help="Set Weekly threshold (0-100)")
    parser.add_argument("--ag-5h", type=float, default=None, help="Set Antigravity 5h threshold (0-100)")
    parser.add_argument("--ag-weekly", type=float, default=None, help="Set Antigravity Weekly threshold (0-100)")
    parser.add_argument("--claude", type=float, default=None, help="Set Claude 3P threshold (0-100)")
    parser.add_argument("--copilot", type=float, default=None, help="Set Copilot threshold (AIC)")
    parser.add_argument("--codex", type=float, default=None, help="Set Codex threshold (%%)")
    parser.add_argument("--set-scope", choices=["all", "low_only"], default=None, help="Set alert scope: 'all' or 'low_only'")
    parser.add_argument("--show-breakdown", choices=["true", "false"], default=None, help="Show agent breakdown: true/false")
    parser.add_argument("--set-5h", type=float, default=None, help="Update current 5h limit remaining percent from UI")
    parser.add_argument("--set-weekly", type=float, default=None, help="Update current Weekly limit remaining percent from UI")
    parser.add_argument("--override-5h", type=float, default=None, help="Override 5h remaining percent for simulation/testing")
    parser.add_argument("--override-weekly", type=float, default=None, help="Override weekly remaining percent for simulation/testing")
    parser.add_argument("--tier", type=str, default=None, help="Current agent tier (low/high/...) for scope checking")
    args = parser.parse_args()

    if (args.set_threshold is not None or args.set_5h_threshold is not None or
        args.set_weekly_threshold is not None or args.ag_5h is not None or
        args.ag_weekly is not None or args.claude is not None or
        args.copilot is not None or args.codex is not None or
        args.set_scope is not None or args.show_breakdown is not None):
        set_thresholds(
            th_all=args.set_threshold,
            th_5h=args.set_5h_threshold,
            th_w=args.set_weekly_threshold,
            ag_5h=args.ag_5h,
            ag_weekly=args.ag_weekly,
            claude=args.claude,
            copilot=args.copilot,
            codex=args.codex,
            scope=args.set_scope,
            show_breakdown=args.show_breakdown,
        )
        print("[Quota Meter] Successfully updated alert configuration.")
        return

    if args.set_5h is not None or args.set_weekly is not None:
        set_calibrated_limits(args.set_5h, args.set_weekly)
        print(f"[Quota Meter] Successfully synced calibrated limits: 5h={args.set_5h}%, Weekly={args.set_weekly}%")
        return

    telemetry = get_dual_quota_telemetry(
        conv_id=args.conv_id,
        five_h_override=args.override_5h,
        weekly_override=args.override_weekly,
        tier=args.tier,
    )

    if args.json:
        print(json.dumps(telemetry, indent=2, ensure_ascii=False))
    elif args.markdown:
        print(format_markdown_footer(telemetry))
    else:
        reset_5h_str = format_local_time(telemetry.get("reset5h"))
        reset_w_str = format_local_time(telemetry.get("resetWeekly"))
        print(f"=== 쿼터 현황 (기준: {telemetry['fiveHourThreshold']}%) ===")
        print(f"5시간 한도 : {telemetry['fiveHourRemainingPercent']}% (리셋: {reset_5h_str or '정보 없음'}) | 최근 5h: {telemetry['tokens5h']:,} tokens")
        print(f"주간 한도   : {telemetry['weeklyRemainingPercent']}% (리셋: {reset_w_str or '정보 없음'}) | 세션: {telemetry['sessionTokens']:,} tokens")
        ext = telemetry.get("externalProviders", {})
        ext_parts = []
        if ext.get("copilot", {}).get("loggedIn"):
            cp_user = ext['copilot'].get('user', '')
            cp_cred = ext['copilot'].get('credits', 0.0)
            ext_parts.append(f"Copilot ({cp_user} · {cp_cred} AIC)")
        if ext.get("claude", {}).get("loggedIn"):
            c_plan = ext['claude'].get('plan', 'pro').upper()
            c_quota = f" · 3P 쿼터: {telemetry['claudeGptWeeklyPercent']:.1f}%" if telemetry.get("claudeGptWeeklyPercent") is not None else ""
            ext_parts.append(f"Claude ({c_plan}{c_quota})")
        if ext.get("codex", {}).get("loggedIn"):
            ext_parts.append("Codex (ChatGPT 연동)")
        if ext_parts:
            print("외부 AI 연동: " + " · ".join(ext_parts))
        if telemetry.get("showAgentBreakdown", False):
            agents = telemetry.get("agentBreakdown", [])
            if len(agents) > 1:
                print("에이전트별 : " + " · ".join(f"{a['name']} ({a['tokens']:,}t)" for a in agents))
        if telemetry.get("alertTriggered", False):
            print(f"⚠️ 쿼터 주의 : {telemetry['recommendation']}")
        else:
            print("상태       : 정상 (기준치 초과)")


if __name__ == "__main__":
    main()
