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
        os.replace(tmp_path, path)
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


def get_dual_quota_telemetry(conv_id=None, brain_dir=None, now_utc=None, five_h_override=None, weekly_override=None):
    config = load_json(CONFIG_PATH, {})
    state = load_json(STATE_PATH, {})

    quota_cfg = config.get("quotaMonitoring", {})
    thresholds = quota_cfg.get("thresholds", {})
    th_5h = thresholds.get("fiveHourLimitPercent", quota_cfg.get("lowQuotaThresholdPercent", 70))
    th_weekly = thresholds.get("weeklyLimitPercent", quota_cfg.get("lowQuotaThresholdPercent", 70))

    calibrated = quota_cfg.get("calibratedLimits", {})
    base_5h = calibrated.get("fiveHourRemainingPercent", 72.0)
    base_weekly = calibrated.get("weeklyRemainingPercent", 93.0)

    rem_5h = float(five_h_override) if five_h_override is not None else float(base_5h)
    rem_weekly = float(weekly_override) if weekly_override is not None else float(base_weekly)

    if not conv_id:
        conv_id = find_latest_conversation_id(brain_dir) or state.get("coordinatorConversationId")

    session_tokens = compute_conversation_tokens(conv_id, brain_dir)
    tokens_5h, steps_5h = compute_5h_rolling_tokens(brain_dir, now_utc)

    is_low_5h = rem_5h <= th_5h
    is_low_weekly = rem_weekly <= th_weekly
    is_low_quota = is_low_5h or is_low_weekly

    has_carbon = state.get("hasCarbon", False) or config.get("enableCarbon", False)

    recommendation = None
    if is_low_5h and is_low_weekly:
        recommendation = (
            f"5h Limit({rem_5h:.1f}%)과 Weekly Limit({rem_weekly:.1f}%)이 모두 기준치({th_5h}%) 이하입니다. "
            "즉시 gemini-4-neon-low(경량) 또는 0쿼터 모델로 전환하여 사용량을 보존하세요."
        )
    elif is_low_5h:
        recommendation = (
            f"5h Limit({rem_5h:.1f}%)이 기준({th_5h}% 이하)에 도달했습니다. "
            "슬라이딩 윈도우 회복 전까지 1~2시간 동안 경량 모델(gemini-4-neon-low) 사용을 권장합니다."
        )
    elif is_low_weekly:
        recommendation = (
            f"Weekly Limit({rem_weekly:.1f}%)이 기준({th_weekly}% 이하)에 도달했습니다. "
            "이번 주 남은 일정을 위해 Carbon/Argon 고사양 모델 호출을 자제하고 표준 티어를 권장합니다."
        )

    return {
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
        "hasCarbon": has_carbon,
        "recommendation": recommendation,
    }


def make_bar(percent, total_blocks=15):
    filled = min(total_blocks, max(0, int(round((percent / 100.0) * total_blocks))))
    empty = total_blocks - filled
    return "█" * filled + "░" * empty


def format_markdown_footer(telemetry):
    p_5h = telemetry["fiveHourRemainingPercent"]
    p_w = telemetry["weeklyRemainingPercent"]
    th_5h = telemetry["fiveHourThreshold"]
    th_w = telemetry["weeklyThreshold"]
    bar_5h = make_bar(p_5h)
    bar_w = make_bar(p_w)

    session_t = f"{telemetry['sessionTokens']:,}"
    rolling_5h_t = f"{telemetry['tokens5h']:,}"

    lines = [
        "---",
        "> [!NOTE] **Antigravity Dual Quota Telemetry**",
        f"> • **5h Limit (단기 롤링)**  : `[{bar_5h}]` **{p_5h:.1f}%** (기준: {th_5h}% 이하 시 경고) | 최근 5시간: `{rolling_5h_t}` tokens",
        f"> • **Weekly Limit (주간 총량)**: `[{bar_w}]` **{p_w:.1f}%** (기준: {th_w}% 이하 시 경고) | 세션 누적: `{session_t}` tokens",
        f"> • **Carbon 플래그십**        : `{'활성 (Active - 전면 개방)' if telemetry['hasCarbon'] else '미가용'}`",
    ]

    if telemetry["isLowQuota"]:
        lines.append(f"> • ⚠️ **쿼터 주의 (5h Limit: {p_5h:.1f}%, Weekly Limit: {p_w:.1f}%)**: {telemetry['recommendation']}")

    return "\n".join(lines)


def set_thresholds(th_all=None, th_5h=None, th_w=None):
    config = load_json(CONFIG_PATH, {})
    q = config.setdefault("quotaMonitoring", {})
    t = q.setdefault("thresholds", {})

    if th_all is not None:
        val = int(th_all)
        t["fiveHourLimitPercent"] = val
        t["weeklyLimitPercent"] = val
        q["lowQuotaThresholdPercent"] = val
    if th_5h is not None:
        t["fiveHourLimitPercent"] = int(th_5h)
    if th_w is not None:
        t["weeklyLimitPercent"] = int(th_w)

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
    parser.add_argument("--set-threshold", type=int, default=None, help="Set threshold (1-99) for both 5h and Weekly")
    parser.add_argument("--set-5h-threshold", type=int, default=None, help="Set 5h threshold (1-99)")
    parser.add_argument("--set-weekly-threshold", type=int, default=None, help="Set Weekly threshold (1-99)")
    parser.add_argument("--set-5h", type=float, default=None, help="Update current 5h limit remaining percent from UI")
    parser.add_argument("--set-weekly", type=float, default=None, help="Update current Weekly limit remaining percent from UI")
    args = parser.parse_args()

    if args.set_threshold or args.set_5h_threshold or args.set_weekly_threshold:
        set_thresholds(args.set_threshold, args.set_5h_threshold, args.set_weekly_threshold)
        print("[Quota Meter] Successfully updated threshold configuration.")
        return

    if args.set_5h is not None or args.set_weekly is not None:
        set_calibrated_limits(args.set_5h, args.set_weekly)
        print(f"[Quota Meter] Successfully synced calibrated limits: 5h={args.set_5h}%, Weekly={args.set_weekly}%")
        return

    telemetry = get_dual_quota_telemetry(conv_id=args.conv_id)

    if args.json:
        print(json.dumps(telemetry, indent=2, ensure_ascii=False))
    elif args.markdown:
        print(format_markdown_footer(telemetry))
    else:
        print("=== Antigravity Dual Quota Telemetry ===")
        print(f"5h Limit Remaining     : {telemetry['fiveHourRemainingPercent']}% (Threshold: {telemetry['fiveHourThreshold']}%)")
        print(f"Weekly Limit Remaining : {telemetry['weeklyRemainingPercent']}% (Threshold: {telemetry['weeklyThreshold']}%)")
        print(f"Recent 5h Tokens       : {telemetry['tokens5h']:,} across {telemetry['steps5h']} steps")
        print(f"Session Tokens         : {telemetry['sessionTokens']:,}")
        print(f"Low Quota Alert Active : {telemetry['isLowQuota']}")
        if telemetry["isLowQuota"]:
            print(f"ALERT: {telemetry['recommendation']}")


if __name__ == "__main__":
    main()
