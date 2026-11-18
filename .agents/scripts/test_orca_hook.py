import json
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK_SCRIPT = os.path.join(BASE_DIR, "scripts", "orca_hook.py")
CONFIG_PATH = os.path.join(BASE_DIR, "orca-config.json")


def run_hook(payload):
    proc = subprocess.Popen(
        [sys.executable, "-X", "utf8", HOOK_SCRIPT],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    stdout, stderr = proc.communicate(input=json.dumps(payload, ensure_ascii=False))
    if proc.returncode != 0:
        raise RuntimeError(f"Hook failed ({proc.returncode}): {stderr}")
    try:
        return json.loads(stdout.strip())
    except Exception as e:
        raise ValueError(f"Failed to parse hook output: {stdout}") from e


def test_suite():
    tests = [
        # Explicit tier alias tests
        {
            "name": "Explicit 'low' -> gemini-4-hydrogen-low",
            "payload": {
                "conversationId": "c1",
                "toolCall": {"name": "swarm", "args": {"action": "add", "model": "low", "brief": "Do work"}}
            },
            "expected_model": "gemini-4-hydrogen-low"
        },
        {
            "name": "Explicit 'medium' -> gemini-4-hydrogen-medium",
            "payload": {
                "conversationId": "c1",
                "toolCall": {"name": "swarm", "args": {"action": "add", "model": "medium", "brief": "Do work"}}
            },
            "expected_model": "gemini-4-hydrogen-medium"
        },
        {
            "name": "Explicit 'flash-medium' -> gemini-3.8-flash-medium",
            "payload": {
                "conversationId": "c1",
                "toolCall": {"name": "swarm", "args": {"action": "add", "model": "flash-medium", "brief": "Do work"}}
            },
            "expected_model": "gemini-3.8-flash-medium"
        },
        {
            "name": "Explicit full model 'gemini-4-argon-high'",
            "payload": {
                "conversationId": "c1",
                "toolCall": {"name": "swarm", "args": {"action": "add", "model": "gemini-4-argon-high", "brief": "Do work"}}
            },
            "expected_model": "gemini-4-argon-high"
        },
        # Adaptive tests with model=None or "auto"
        {
            "name": "Adaptive: Concurrency / Deadlock / RMI -> gemini-4-argon-high",
            "payload": {
                "conversationId": "c1",
                "toolCall": {"name": "swarm", "args": {"action": "add", "model": "auto", "brief": "Investigate RMI distributed deadlock and concurrency race condition"}}
            },
            "expected_model": "gemini-4-argon-high"
        },
        {
            "name": "Adaptive Korean: 동시성 / 아키텍처 -> gemini-4-argon-high",
            "payload": {
                "conversationId": "c1",
                "toolCall": {"name": "swarm", "args": {"action": "add", "brief": "서버 아키텍처 설계 및 분산 동시성 이슈 분석"}}
            },
            "expected_model": "gemini-4-argon-high"
        },
        {
            "name": "Adaptive: Complex / Benchmark -> gemini-4-hydrogen-xhigh",
            "payload": {
                "conversationId": "c1",
                "toolCall": {"name": "swarm", "args": {"action": "add", "model": "auto", "brief": "Run heavy benchmark and complex multi-module test suite"}}
            },
            "expected_model": "gemini-4-hydrogen-xhigh"
        },
        {
            "name": "Adaptive: Documentation / Format / Gitignore -> gemini-3.8-flash-high",
            "payload": {
                "conversationId": "c1",
                "toolCall": {"name": "swarm", "args": {"action": "add", "model": "auto", "brief": "Update .gitignore and README formatting docs"}}
            },
            "expected_model": "gemini-3.8-flash-high"
        },
        {
            "name": "Adaptive: Standard Feature Implementation -> gemini-4-hydrogen-high",
            "payload": {
                "conversationId": "c1",
                "toolCall": {"name": "swarm", "args": {"action": "add", "model": "auto", "brief": "Implement student registration feature and unit test"}}
            },
            "expected_model": "gemini-4-hydrogen-high"
        },
        {
            "name": "Adaptive Fallback: Generic brief -> gemini-4-hydrogen-high",
            "payload": {
                "conversationId": "c1",
                "toolCall": {"name": "swarm", "args": {"action": "add", "model": "auto", "brief": "Miscellaneous general worker"}}
            },
            "expected_model": "gemini-4-hydrogen-high"
        },
        # Carbon Forward-Compatibility tests (default: enableCarbon=false -> graceful fallback)
        {
            "name": "Carbon Fallback: Explicit 'carbon' with enableCarbon=false -> gemini-4-argon-high",
            "payload": {
                "conversationId": "c1",
                "toolCall": {"name": "swarm", "args": {"action": "add", "model": "carbon", "brief": "High reasoning task"}}
            },
            "expected_model": "gemini-4-argon-high"
        },
        {
            "name": "Carbon Fallback: Explicit 'gemini-4-carbon-high' with enableCarbon=false -> gemini-4-argon-high",
            "payload": {
                "conversationId": "c1",
                "toolCall": {"name": "swarm", "args": {"action": "add", "model": "gemini-4-carbon-high", "brief": "High reasoning task"}}
            },
            "expected_model": "gemini-4-argon-high"
        },
    ]

    all_passed = True
    print("=== ORCA Adaptive Effort Test Suite ===")
    for t in tests:
        res = run_hook(t["payload"])
        actual_model = (
            res.get("overwrite", {}).get("model")
            or t["payload"]["toolCall"]["args"].get("model")
        )
        if actual_model == t["expected_model"]:
            print(f"[PASS] {t['name']} -> {actual_model}")
        else:
            print(f"[FAIL] {t['name']}: expected {t['expected_model']}, got {actual_model} (res={res})")
            all_passed = False

    # Carbon Enabled tests (temporarily set enableCarbon=true)
    print("\n=== Carbon Enabled Environment Tests ===")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["enableCarbon"] = True
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

    try:
        carbon_tests = [
            {
                "name": "Carbon Enabled: Explicit 'carbon' -> gemini-4-carbon-high",
                "payload": {
                    "conversationId": "c1",
                    "toolCall": {"name": "swarm", "args": {"action": "add", "model": "carbon", "brief": "High reasoning task"}}
                },
                "expected_model": "gemini-4-carbon-high"
            },
            {
                "name": "Carbon Enabled: Adaptive concurrency task -> gemini-4-carbon-high",
                "payload": {
                    "conversationId": "c1",
                    "toolCall": {"name": "swarm", "args": {"action": "add", "model": "auto", "brief": "분산 아키텍처 및 동시성 데드락 해결"}}
                },
                "expected_model": "gemini-4-carbon-high"
            },
        ]
        for t in carbon_tests:
            res = run_hook(t["payload"])
            actual_model = (
                res.get("overwrite", {}).get("model")
                or t["payload"]["toolCall"]["args"].get("model")
            )
            if actual_model == t["expected_model"]:
                print(f"[PASS] {t['name']} -> {actual_model}")
            else:
                print(f"[FAIL] {t['name']}: expected {t['expected_model']}, got {actual_model} (res={res})")
                all_passed = False
    finally:
        # Restore enableCarbon=false
        cfg["enableCarbon"] = False
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)

    # Test file edit guard
    print("\n=== ORCA Guard File Edit Gating Tests ===")
    blocked_edit = run_hook({
        "conversationId": "coord-conv",
        "modelName": "gemini-3.8-flash-high",
        "toolCall": {"name": "edit_file", "args": {"Path": "c:\\Users\\alswo\\project\\src\\Main.java"}}
    })
    if blocked_edit.get("decision") == "deny":
        print("[PASS] Coordinator edit outside exempt path is BLOCKED")
    else:
        print(f"[FAIL] Expected deny, got: {blocked_edit}")
        all_passed = False

    allowed_edit = run_hook({
        "conversationId": "coord-conv",
        "modelName": "gemini-3.8-flash-high",
        "toolCall": {"name": "write_file", "args": {"Path": "c:\\Users\\alswo\\gemineone\\GEMINI.md"}}
    })
    if allowed_edit.get("decision") == "allow":
        print("[PASS] Coordinator edit inside exempt path (GEMINI.md) is ALLOWED")
    else:
        print(f"[FAIL] Expected allow, got: {allowed_edit}")
        all_passed = False

    if all_passed:
        print("\nAll 16 tests passed successfully!")
    else:
        sys.exit(1)


if __name__ == "__main__":
    test_suite()
