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


def set_user_threshold(new_threshold):
    try:
        val = int(new_threshold)
        if not (1 <= val <= 99):
            raise ValueError("Threshold must be between 1 and 99")
    except ValueError as e:
        raise ValueError(f"Invalid threshold '{new_threshold}': must be an integer between 1 and 99") from e

    config = load_json(CONFIG_PATH, {})
    if "quotaMonitoring" not in config:
        config["quotaMonitoring"] = {
            "enabled": True,
            "dailyTokenBaseline": 5000000,
            "displayInSummary": True
        }
    config["quotaMonitoring"]["lowQuotaThresholdPercent"] = val
    save_json(CONFIG_PATH, config)
    return val


def get_default_brain_dir():
    user_home = os.environ.get("USERPROFILE", os.path.expanduser("~"))
    return os.path.join(user_home, ".gemini", "antigravity", "brain")


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
                if mtime != target_date:
                    continue
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            d = json.loads(line)
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


def get_quota_telemetry(conv_id=None, brain_dir=None, target_date=None, threshold_override=None):
    config = load_json(CONFIG_PATH, {})
    state = load_json(STATE_PATH, {})

    quota_cfg = config.get("quotaMonitoring", {})
    baseline = quota_cfg.get("dailyTokenBaseline", 5000000)

    # Threshold priority:
    # 1. Explicit runtime parameter override
    # 2. Environment variable ORCA_LOW_QUOTA_THRESHOLD
    # 3. User setting in orca-config.json
    # 4. Default 25%
    if threshold_override is not None:
        low_thresh = int(threshold_override)
    elif os.environ.get("ORCA_LOW_QUOTA_THRESHOLD"):
        try:
            low_thresh = int(os.environ.get("ORCA_LOW_QUOTA_THRESHOLD"))
        except ValueError:
            low_thresh = quota_cfg.get("lowQuotaThresholdPercent", 25)
    else:
        low_thresh = quota_cfg.get("lowQuotaThresholdPercent", 25)

    if not conv_id:
        conv_id = state.get("coordinatorConversationId")

    session_tokens = compute_conversation_tokens(conv_id, brain_dir)
    daily_tokens, total_steps = compute_today_tokens(brain_dir, target_date)

    used_percent = round((daily_tokens / baseline) * 100, 1) if baseline > 0 else 0.0
    remaining_percent = max(0.0, round(100.0 - used_percent, 1))
    is_low_quota = remaining_percent <= low_thresh

    has_carbon = state.get("hasCarbon", False) or config.get("enableCarbon", False)

    recommendation = None
    if is_low_quota:
        recommendation = (
            f"일일 잔여 쿼터({remaining_percent}%)가 사용자 지정 알림 기준({low_thresh}%) 이하입니다. "
            "다음 작업은 gemini-4-neon-low(경량) 또는 GitHub Copilot(0쿼터)으로의 전환을 권장합니다."
        )

    return {
        "conversationId": conv_id,
        "sessionTokens": session_tokens,
        "dailyTokens": daily_tokens,
        "totalStepsToday": total_steps,
        "dailyBaseline": baseline,
        "usedPercent": used_percent,
        "remainingPercent": remaining_percent,
        "isLowQuota": is_low_quota,
        "lowQuotaThreshold": low_thresh,
        "hasCarbon": has_carbon,
        "recommendation": recommendation,
    }


def format_markdown_footer(telemetry):
    rem = telemetry["remainingPercent"]
    is_low = telemetry["isLowQuota"]
    thresh = telemetry["lowQuotaThreshold"]
    session_t = f"{telemetry['sessionTokens']:,}"
    daily_t = f"{telemetry['dailyTokens']:,}"
    baseline_t = f"{telemetry['dailyBaseline']:,}"

    # Visual progress bar (15 blocks)
    total_blocks = 15
    filled = min(total_blocks, max(0, int(round((rem / 100.0) * total_blocks))))
    empty = total_blocks - filled
    bar = "█" * filled + "░" * empty

    lines = [
        "---",
        "> [!NOTE] **Antigravity Quota & Telemetry**",
        f"> • **세션 소모**: `{session_t}` tokens | **오늘 누적**: `{daily_t}` / `{baseline_t}` ({telemetry['usedPercent']}%)",
        f"> • **잔여 쿼터**: `[{bar}]` **{rem}%** | **Carbon 플래그십**: `{'활성 (Active)' if telemetry['hasCarbon'] else '미가용'}`",
    ]

    if is_low:
        lines.append(f"> • ⚠️ **쿼터 주의 (사용자 지정 기준: {thresh}% 이하)**: {telemetry['recommendation']}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Antigravity Quota Meter")
    parser.add_argument("--json", action="store_true", help="Output telemetry as JSON")
    parser.add_argument("--markdown", action="store_true", help="Output telemetry as Markdown footer")
    parser.add_argument("--conv-id", type=str, default=None, help="Conversation ID to inspect")
    parser.add_argument("--threshold", type=int, default=None, help="Temporary threshold percentage override (1-99)")
    parser.add_argument("--set-threshold", type=int, default=None, help="Persistently set low quota alert threshold (1-99) in orca-config.json")
    args = parser.parse_args()

    if args.set_threshold is not None:
        try:
            val = set_user_threshold(args.set_threshold)
            print(f"[Quota Meter] Successfully updated low quota alert threshold to {val}% in orca-config.json")
            return
        except Exception as e:
            print(f"[Quota Meter] Error: {e}", file=sys.stderr)
            sys.exit(1)

    telemetry = get_quota_telemetry(conv_id=args.conv_id, threshold_override=args.threshold)

    if args.json:
        print(json.dumps(telemetry, indent=2, ensure_ascii=False))
    elif args.markdown:
        print(format_markdown_footer(telemetry))
    else:
        print("=== Antigravity Quota Telemetry ===")
        print(f"Session Tokens : {telemetry['sessionTokens']:,}")
        print(f"Today Tokens   : {telemetry['dailyTokens']:,} across {telemetry['totalStepsToday']} steps")
        print(f"Daily Baseline : {telemetry['dailyBaseline']:,}")
        print(f"Remaining      : {telemetry['remainingPercent']}% (Used: {telemetry['usedPercent']}%)")
        print(f"User Threshold : {telemetry['lowQuotaThreshold']}%")
        print(f"Carbon Active  : {telemetry['hasCarbon']}")
        if telemetry["isLowQuota"]:
            print(f"ALERT: {telemetry['recommendation']}")


if __name__ == "__main__":
    main()
