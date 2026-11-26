#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gemineone ORCA Orchestrator Unified CLI
Single entry point for orchestration management, configuration, model sync, and subagent dispatching.
"""

import argparse
import json
import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(BASE_DIR, "orca-config.json")
STATE_PATH = os.path.join(BASE_DIR, ".orca-state.json")

if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import quota_meter


UI_DIR = os.path.join(BASE_DIR, "ui")


def stage_ui_artifacts(target_artifact_dir=None):
    """
    Stage UI html templates from .agents/ui/ to the active Antigravity conversation artifact directory.
    Ensures seamless generative UI rendering across different machines and conversations.
    """
    if not os.path.exists(UI_DIR):
        return None, []

    if not target_artifact_dir:
        brain_root = os.path.expanduser(r"~\.gemini\antigravity\brain")
        if os.path.exists(brain_root):
            conv_dirs = [
                os.path.join(brain_root, d)
                for d in os.listdir(brain_root)
                if os.path.isdir(os.path.join(brain_root, d)) and not d.startswith(".")
            ]
            if conv_dirs:
                conv_dirs.sort(key=lambda p: os.path.getmtime(p), reverse=True)
                target_artifact_dir = conv_dirs[0]

    if target_artifact_dir and os.path.exists(target_artifact_dir):
        import shutil
        staged = []
        telemetry_json = None
        try:
            telemetry = quota_meter.get_dual_quota_telemetry()
            telemetry_json = json.dumps(telemetry, ensure_ascii=False)
        except Exception:
            pass

        for fname in ["orca_settings.html", "orca_models.html", "orca_control_center.html"]:
            src = os.path.join(UI_DIR, fname)
            dst = os.path.join(target_artifact_dir, fname)
            if os.path.exists(src):
                try:
                    if telemetry_json and fname == "orca_control_center.html":
                        with open(src, "r", encoding="utf-8") as f_in:
                            content = f_in.read()
                        if "/* __ORCA_INJECT_DATA__ */" in content:
                            import re
                            content = re.sub(
                                r"/\* __ORCA_INJECT_DATA__ \*/\s*window\.__ORCA_DATA__\s*=\s*window\.__ORCA_DATA__\s*\|\|\s*\{.*?\};",
                                f"/* __ORCA_INJECT_DATA__ */\n    window.__ORCA_DATA__ = {telemetry_json};",
                                content,
                                flags=re.DOTALL
                            )
                        with open(dst, "w", encoding="utf-8") as f_out:
                            f_out.write(content)
                    else:
                        shutil.copy2(src, dst)
                    staged.append(dst)
                except Exception:
                    try:
                        shutil.copy2(src, dst)
                        staged.append(dst)
                    except Exception:
                        pass
        return target_artifact_dir, staged
    return None, []


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
        print(f"[ORCA CLI] Error saving {path}: {e}", file=sys.stderr)
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        raise


def cmd_status(args):
    config = load_json(CONFIG_PATH, {})
    state = load_json(STATE_PATH, {})

    telemetry = quota_meter.get_dual_quota_telemetry()
    p_5h = telemetry.get("fiveHourRemainingPercent", 0.0)
    p_w = telemetry.get("weeklyRemainingPercent", 0.0)
    reset_5h = quota_meter.format_local_time(telemetry.get("reset5h"))
    reset_w = quota_meter.format_local_time(telemetry.get("resetWeekly"))
    c_3p = telemetry.get("claudeGptWeeklyPercent")

    ext = telemetry.get("externalProviders", {})

    print("🧭 [ORCA Orchestration Status]")
    print(f"• 엔진 버전     : gemineone v{config.get('version', '0.4.0')}")
    print(f"• 메인 코디네이터: gemini-3.8-flash-high (1D Fast Intake)")
    print(f"• 기본 작업 티어 : {config.get('defaultTier', 'hydrogen-high')}")

    print("\n📦 [에이전트별 상태 및 쿼터 현황]")

    # 1. Google Antigravity
    print("┌─ [Google Antigravity]")
    print(f"│  • 5시간 한도 (1P)     : {p_5h:.1f}% (리셋: {reset_5h or '정보 없음'} · 5시간 슬라이딩 롤링)")
    print(f"│  • 주간 한도 (1P)      : {p_w:.1f}% (리셋: {reset_w or '정보 없음'} · 주 1회 일괄 충전)")
    if c_3p is not None:
        print(f"│  • 3P 주간쿼터(Claude/GPT): {c_3p:.1f}% (안티그래비티 내부 모델 · 주 1회 일괄 충전)")
    print("│")

    # 2. GitHub Copilot & GitHub CLI
    cp = ext.get("copilot", {})
    gh = ext.get("gh", {})
    gh_rate = gh.get("rateLimit", {})
    print("├─ [GitHub Copilot (gh copilot / copilot CLI)]")
    if cp.get("installed") and cp.get("loggedIn"):
        print(f"│  • 연동 계정   : 정상 연동 ({cp.get('user')}) · v{cp.get('version', '1.0')}")
        print(f"│  • 쿼터 체계   : AI Credits (AIC) / 갱신: 월간 결제일 00:00 UTC + 분당 속도 제어")
    elif cp.get("installed"):
        print(f"│  • 연동 상태   : 설치됨 (로그인 필요)")
    else:
        print(f"│  • 연동 상태   : 미설치")

    if gh.get("installed") and gh.get("loggedIn"):
        core_rem = gh_rate.get("coreRemaining")
        core_lim = gh_rate.get("coreLimit", 5000)
        core_str = f"{core_rem}/{core_lim}" if core_rem is not None else "조회 완료"
        print(f"│  • GitHub CLI : 정상 연동 ({gh.get('user')}) · REST API: {core_str} (갱신: 1시간 슬라이딩 윈도우)")
    elif gh.get("installed"):
        print(f"│  • GitHub CLI : 설치됨 (인증 대기)")
    else:
        print(f"│  • GitHub CLI : 미설치")
    print("│")

    # 3. OpenAI Codex
    cdx = ext.get("codex", {})
    print("├─ [OpenAI Codex]")
    if cdx.get("installed") and cdx.get("loggedIn"):
        user_info = cdx.get("email") or "ChatGPT"
        plan_info = f" ({cdx.get('plan', 'free').upper()} 플랜)" if cdx.get("plan") else ""
        print(f"│  • 인증 계정  : 정상 연동 · {user_info}{plan_info}")
        print(f"│  • 기본 모델  : {cdx.get('model', 'gpt-6-luna')} (사고 수준: {cdx.get('reasoningEffort', 'medium')})")
        print(f"│  • 쿼터 체계  : 3시간 슬라이딩 롤링 윈도우 (메시지 캡 순차 회복)")
    elif cdx.get("installed"):
        print(f"│  • 연동 상태  : 설치됨 (인증 필요: codex login)")
    else:
        print(f"│  • 연동 상태  : 미설치")
    print("│")

    # 4. Anthropic Claude Code (독립 CLI)
    cld = ext.get("claude", {})
    print("└─ [Anthropic Claude Code (독립 CLI)]")
    if cld.get("installed"):
        msg_cnt = cld.get("totalMessages", 0)
        days = cld.get("daysTracked", 0)
        stats_str = f" · 로컬 활동: {days}일간 {msg_cnt:,}개 메시지 기록" if msg_cnt else ""
        log_str = "정상 연동" if cld.get("loggedIn") else "설치됨 (로그인 대기: claude auth login)"
        print(f"   • 연동 상태  : {log_str}{stats_str}")
        print(f"   • 바이너리  : v{cld.get('version', '2.1.332')}")
        print(f"   • 쿼터 체계  : 5시간 슬라이딩 롤링 윈도우 (메시지 한도 점진 복원)")
    else:
        print(f"   • 연동 상태  : 미설치")


def cmd_setting(args):
    config = load_json(CONFIG_PATH, {})
    q = config.setdefault("quotaMonitoring", {})
    a = q.setdefault("alertSettings", {})
    t = q.setdefault("thresholds", {})
    ag_dict = a.setdefault("agents", {})

    modified = False

    if args.threshold is not None:
        val = float(args.threshold)
        a["thresholdPercent"] = val
        a["fiveHourThresholdPercent"] = val
        a["weeklyThresholdPercent"] = val
        t["fiveHourLimitPercent"] = val
        t["weeklyLimitPercent"] = val
        q["lowQuotaThresholdPercent"] = val
        ag_dict.setdefault("antigravity_5h", {})["threshold"] = val
        ag_dict.setdefault("antigravity_weekly", {})["threshold"] = val
        modified = True

    if args.ag_5h is not None or args.threshold_5h is not None:
        val_5h = float(args.ag_5h if args.ag_5h is not None else args.threshold_5h)
        a["fiveHourThresholdPercent"] = val_5h
        t["fiveHourLimitPercent"] = val_5h
        ag_dict.setdefault("antigravity_5h", {})["threshold"] = val_5h
        modified = True

    if args.ag_weekly is not None or args.threshold_weekly is not None:
        val_w = float(args.ag_weekly if args.ag_weekly is not None else args.threshold_weekly)
        a["weeklyThresholdPercent"] = val_w
        t["weeklyLimitPercent"] = val_w
        ag_dict.setdefault("antigravity_weekly", {})["threshold"] = val_w
        modified = True

    if args.claude is not None:
        val_c = float(args.claude)
        ag_dict.setdefault("claude_3p", {})["threshold"] = val_c
        modified = True

    if args.copilot is not None:
        val_cp = float(args.copilot)
        ag_dict.setdefault("copilot", {})["threshold"] = val_cp
        modified = True

    if args.codex is not None:
        val_cdx = float(args.codex)
        ag_dict.setdefault("codex", {})["threshold"] = val_cdx
        modified = True

    if args.scope is not None:
        a["alertScope"] = args.scope
        modified = True

    if args.show_breakdown is not None:
        a["showAgentBreakdown"] = (args.show_breakdown.lower() == "true")
        modified = True

    if args.default_tier is not None:
        config["defaultTier"] = args.default_tier
        modified = True

    if getattr(args, "enforce_worker", None) is not None:
        config["enforceWorkerForEdits"] = (args.enforce_worker.lower() == "true")
        modified = True

    if getattr(args, "adaptive_effort", None) is not None:
        config.setdefault("adaptiveEffort", {})["enabled"] = (args.adaptive_effort.lower() == "true")
        modified = True

    if getattr(args, "token_baseline", None) is not None:
        q["dailyTokenBaseline"] = int(args.token_baseline)
        modified = True

    if modified:
        save_json(CONFIG_PATH, config)
        print("[ORCA] Settings successfully updated.")

    if getattr(args, "ui", False):
        import webbrowser
        target_dir, staged = stage_ui_artifacts()
        settings_html = os.path.join(UI_DIR, "orca_settings.html")
        if target_dir:
            staged_html = os.path.join(target_dir, "orca_settings.html")
            if os.path.exists(staged_html):
                settings_html = staged_html
        print(f"[ORCA UI] Settings Hub UI: {settings_html}")
        try:
            webbrowser.open(f"file:///{os.path.abspath(settings_html).replace(os.sep, '/')}")
        except Exception:
            pass
        return

    if args.json:
        print(json.dumps({
            "version": config.get("version"),
            "defaultTier": config.get("defaultTier"),
            "enforceWorkerForEdits": config.get("enforceWorkerForEdits", True),
            "adaptiveEffortEnabled": config.get("adaptiveEffort", {}).get("enabled", True),
            "dailyTokenBaseline": q.get("dailyTokenBaseline", 5000000),
            "alertSettings": a,
        }, indent=2, ensure_ascii=False))
    else:
        print("=== [ORCA Settings] ===")
        print(f"• 5h Alert Threshold   : {a.get('fiveHourThresholdPercent', 25.0)}%")
        print(f"• Weekly Threshold     : {a.get('weeklyThresholdPercent', 25.0)}%")
        print(f"• Alert Scope          : {a.get('alertScope', 'all')} (all | low_only)")
        print(f"• Show Token Breakdown : {a.get('showAgentBreakdown', False)}")
        print(f"• Default Worker Tier  : {config.get('defaultTier', 'hydrogen-high')}")
        print(f"• Enforce Worker Edits : {config.get('enforceWorkerForEdits', True)}")
        print(f"• Adaptive Effort      : {config.get('adaptiveEffort', {}).get('enabled', True)}")
        if ag_dict:
            print("• 에이전트별 기준치     :")
            for k, info in ag_dict.items():
                print(f"  - {k:<18}: {info.get('threshold')}")


def cmd_model(args):
    config = load_json(CONFIG_PATH, {})
    modified = False

    # 1. Mutate if arguments provided
    if getattr(args, "coordinator", None):
        new_coord = args.coordinator
        config["coordinatorModel"] = new_coord
        modified = True
        print(f"[ORCA] Main coordinator model set to: {new_coord}")

    if getattr(args, "worker", None):
        new_w = args.worker
        config["defaultTier"] = new_w
        modified = True
        print(f"[ORCA] Default worker tier set to: {new_w}")

    rules = config.setdefault("adaptiveEffort", {}).setdefault("rules", [])
    rule_map = {r.get("name"): r for r in rules}

    sub_updates = {
        "deep_architecture_concurrency": args.arch,
        "complex_implementation_debug": args.debug,
        "standard_development_test": args.dev,
        "light_scripting_edit": args.light,
        "boilerplate_config_docs": args.docs,
    }
    for r_name, target in sub_updates.items():
        if target:
            if r_name in rule_map:
                rule_map[r_name]["targetModel"] = target
            else:
                rules.append({"name": r_name, "targetModel": target, "keywords": []})
            modified = True
            print(f"[ORCA] Coworker rule '{r_name}' target model set to: {target}")

    if modified:
        save_json(CONFIG_PATH, config)
        print("[ORCA] Model configuration successfully saved.")

    # 2. Output
    coord_model = config.get("coordinatorModel", "gemini-3.8-flash-high")
    default_tier = config.get("defaultTier", "hydrogen-high")
    tiers = config.get("tiers", {})
    resolved_default_worker = tiers.get(default_tier, default_tier)

    if getattr(args, "ui", False):
        import webbrowser
        target_dir, staged = stage_ui_artifacts()
        models_html = os.path.join(UI_DIR, "orca_models.html")
        if target_dir:
            staged_html = os.path.join(target_dir, "orca_models.html")
            if os.path.exists(staged_html):
                models_html = staged_html
        print(f"[ORCA UI] Models Configuration UI: {models_html}")
        try:
            webbrowser.open(f"file:///{os.path.abspath(models_html).replace(os.sep, '/')}")
        except Exception:
            pass
        return

    if args.json:
        print(json.dumps({
            "coordinatorModel": coord_model,
            "defaultTier": default_tier,
            "defaultWorkerModel": resolved_default_worker,
            "coworkerRules": rules,
            "allowedModels": config.get("allowedWorkerModels", []),
        }, indent=2, ensure_ascii=False))
        return

    print("🧭 [ORCA Model Configuration]")
    print(f"• 메인 대화 모델 (Coordinator) : {coord_model}")
    print(f"• 기본 코워커 모델 (Default Worker): {resolved_default_worker} (티어: {default_tier})")

    print("\n📋 [작업 유형별 코워커 모델 라우팅]")
    name_ko = {
        "deep_architecture_concurrency": "심층 아키텍처 및 동시성",
        "complex_implementation_debug": "복합 디버깅 및 대규모 테스트",
        "standard_development_test": "일반 기능 개발 및 구현",
        "light_scripting_edit": "경량 스크립트 및 단순 수정",
        "boilerplate_config_docs": "보일러플레이트 및 설정/문서",
    }
    for r in rules:
        r_name = r.get("name")
        k_disp = name_ko.get(r_name, r_name)
        m_target = r.get("targetModel")
        print(f"  - {k_disp:<18} : {m_target}")

    if args.list:
        print("\n📦 [선택 가능한 주요 모델 목록]")
        for m in config.get("allowedWorkerModels", []):
            print(f"  • {m}")
    else:
        print("\n💡 [모델 변경 CLI 예시]")
        print("  - 메인 모델 변경   : python .agents/scripts/orca.py model --main gemini-4-neon-high")
        print("  - 기본 코워커 변경 : python .agents/scripts/orca.py model --worker neon-high")
        print("  - 전체 모델 보기   : python .agents/scripts/orca.py model --list")


def cmd_dispatch(args):
    from coworker_bus import CoworkerEventBus
    target = getattr(args, "target", "")
    prompt = getattr(args, "prompt", "")
    files = getattr(args, "files", None)
    model = getattr(args, "model", None)
    read_only = getattr(args, "read_only", False)
    timeout = getattr(args, "timeout", 180)

    print(f"🧭 [ORCA Event Bus] Dispatching task to '{target}'...")
    res = CoworkerEventBus.dispatch(
        target=target,
        task=prompt,
        files=files,
        model=model,
        read_only=read_only,
        timeout=timeout,
    )

    if getattr(args, "json", False):
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return

    if res.get("success"):
        print(f"\n✅ [{target.upper()} Output]:")
        print(res.get("output", ""))
        u = res.get("usage", {})
        if u:
            tot = u.get("totalTokens", 0)
            cred = u.get("credits")
            cred_str = f" ({cred} AIC)" if cred is not None else ""
            print(f"\n📊 [Usage: {tot:,} tokens{cred_str}]")
    else:
        print(f"\n❌ [{target.upper()} Error]: {res.get('error')}", file=sys.stderr)
        sys.exit(1)


def cmd_sync(args):
    print("[ORCA] Syncing live Antigravity models...")
    sync_script = os.path.join(SCRIPT_DIR, "sync_models.py")
    res = subprocess.run([sys.executable, "-X", "utf8", sync_script])
    sys.exit(res.returncode)


def cmd_quota(args):
    quota_script = os.path.join(SCRIPT_DIR, "quota_meter.py")
    cmd = [sys.executable, quota_script, "--markdown"]
    res = subprocess.run(cmd)
    sys.exit(res.returncode)


def cmd_help(args):
    print("""
🧭 gemineone ORCA Orchestrator CLI & Chat Commands (/orca)
===========================================================

[Chat Commands]
  /orca               : Show ORCA Orchestration Control Center
  /orca model         : Inspect and configure main coordinator and coworker models
  /orca setting       : Open interactive Settings UI panel
  /orca status        : Show live models, subagents, and quota
  /orca sync          : Synchronize available models from local account
  /orca quota         : Output real-time dual quota telemetry footer

[Terminal CLI Commands]
  python .agents/scripts/orca.py model [--main <model>] [--worker <tier>] [--ui] [--list]
  python .agents/scripts/orca.py dispatch --target <copilot|codex> -p "<task>"
  python .agents/scripts/orca.py status
  python .agents/scripts/orca.py setting [--ag-5h <N>] [--ag-weekly <N>] [--ui]
  python .agents/scripts/orca.py sync
  python .agents/scripts/orca.py quota
""")


def main():
    parser = argparse.ArgumentParser(description="gemineone ORCA Unified Controller")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # status
    p_status = subparsers.add_parser("status", help="Show orchestration and subagent status")
    p_status.set_defaults(func=cmd_status)

    # model
    p_model = subparsers.add_parser("model", aliases=["models"], help="Inspect or configure models")
    p_model.add_argument("--coordinator", "--main", dest="coordinator", type=str, default=None, help="Set main coordinator model")
    p_model.add_argument("--worker", "--default-worker", dest="worker", type=str, default=None, help="Set default worker tier/model")
    p_model.add_argument("--arch", type=str, default=None, help="Set target model for deep architecture/concurrency")
    p_model.add_argument("--debug", type=str, default=None, help="Set target model for complex debug/benchmarking")
    p_model.add_argument("--dev", type=str, default=None, help="Set target model for standard feature development")
    p_model.add_argument("--light", type=str, default=None, help="Set target model for light scripting/edits")
    p_model.add_argument("--docs", type=str, default=None, help="Set target model for configs, docs, boilerplate")
    p_model.add_argument("--list", action="store_true", help="List all available live models")
    p_model.add_argument("--ui", action="store_true", help="Open Models Configuration HTML UI")
    p_model.add_argument("--json", action="store_true", help="Output models configuration as JSON")
    p_model.set_defaults(func=cmd_model)

    # setting
    p_setting = subparsers.add_parser("setting", aliases=["settings", "config"], help="View or update settings")
    p_setting.add_argument("--ui", action="store_true", help="Open Settings Hub HTML UI")
    p_setting.add_argument("--threshold", type=float, default=None, help="Set both 5h and weekly threshold percent")
    p_setting.add_argument("--threshold-5h", type=float, default=None, help="Set 5h threshold percent")
    p_setting.add_argument("--threshold-weekly", type=float, default=None, help="Set weekly threshold percent")
    p_setting.add_argument("--ag-5h", type=float, default=None, help="Antigravity 5h threshold percent")
    p_setting.add_argument("--ag-weekly", type=float, default=None, help="Antigravity weekly threshold percent")
    p_setting.add_argument("--claude", type=float, default=None, help="Claude 3P threshold percent")
    p_setting.add_argument("--copilot", type=float, default=None, help="GitHub Copilot threshold count/percent")
    p_setting.add_argument("--codex", type=float, default=None, help="OpenAI Codex threshold percent")
    p_setting.add_argument("--scope", choices=["all", "low_only"], default=None, help="Set alert scope")
    p_setting.add_argument("--show-breakdown", choices=["true", "false"], default=None, help="Show token breakdown")
    p_setting.add_argument("--default-tier", type=str, default=None, help="Set default worker tier")
    p_setting.add_argument("--enforce-worker", choices=["true", "false"], default=None, help="Enforce worker for code edits")
    p_setting.add_argument("--adaptive-effort", choices=["true", "false"], default=None, help="Enable adaptive thinking effort")
    p_setting.add_argument("--token-baseline", type=int, default=None, help="Set daily token baseline")
    p_setting.add_argument("--json", action="store_true", help="Output settings as JSON")
    p_setting.set_defaults(func=cmd_setting)

    # sync
    p_sync = subparsers.add_parser("sync", help="Sync models from agy CLI")
    p_sync.set_defaults(func=cmd_sync)

    # dispatch
    p_dispatch = subparsers.add_parser("dispatch", aliases=["delegate", "run"], help="Dispatch task to external coworker (copilot, codex)")
    p_dispatch.add_argument("--target", "-t", required=True, help="Target coworker provider (copilot, codex)")
    p_dispatch.add_argument("--prompt", "-p", required=True, help="Task prompt or instruction")
    p_dispatch.add_argument("--files", "-f", help="Comma-separated context file paths")
    p_dispatch.add_argument("--model", "-m", help="Target model override")
    p_dispatch.add_argument("--read-only", action="store_true", help="Run in read-only mode")
    p_dispatch.add_argument("--timeout", type=int, default=180, help="Timeout in seconds")
    p_dispatch.add_argument("--json", action="store_true", help="Output JSON result")
    p_dispatch.set_defaults(func=cmd_dispatch)

    # quota
    p_quota = subparsers.add_parser("quota", help="Print dual quota markdown meter")
    p_quota.set_defaults(func=cmd_quota)

    # help
    p_help = subparsers.add_parser("help", help="Show command cheat sheet")
    p_help.set_defaults(func=cmd_help)

    args = parser.parse_args()

    if not args.command:
        cmd_help(args)
    else:
        args.func(args)


if __name__ == "__main__":
    main()
