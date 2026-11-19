import json
import os
import subprocess
import sys
import tempfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AGENTS_DIR = os.path.dirname(SCRIPT_DIR)
REPO_ROOT = os.path.dirname(AGENTS_DIR)
INSTALL_BAT = os.path.join(REPO_ROOT, "install.bat")
BOOTSTRAP_SCRIPT = os.path.join(SCRIPT_DIR, "bootstrap.py")

sys.path.insert(0, SCRIPT_DIR)
import bootstrap  # noqa: E402


def run_cmd(cmd, cwd=None):
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    return proc.returncode, proc.stdout, proc.stderr


def assert_true(cond, msg):
    if not cond:
        raise AssertionError(msg)


def test_install_bat_end_to_end():
    """Verify install.bat copies harness, runs bootstrap probe, and creates SETUP.md."""
    with tempfile.TemporaryDirectory(prefix="gemineone_e2e_") as tmpdir:
        code, out, err = run_cmd(["cmd", "/c", INSTALL_BAT, tmpdir])
        assert_true(code == 0, f"install.bat failed (code={code}): stdout={out}\nstderr={err}")
        assert_true("Phase 1 bootstrap complete" in out, f"Missing bootstrap completion output: {out}")

        gemini_md = os.path.join(tmpdir, "GEMINI.md")
        setup_md = os.path.join(tmpdir, "SETUP.md")
        cfg_path = os.path.join(tmpdir, ".agents", "orca-config.json")
        state_path = os.path.join(tmpdir, ".agents", ".orca-state.json")
        hook_script = os.path.join(tmpdir, ".agents", "scripts", "orca_hook.py")

        for p in (gemini_md, setup_md, cfg_path, state_path, hook_script):
            assert_true(os.path.exists(p), f"Expected file not found after install.bat: {p}")

        # Verify transient source artifacts were excluded during installation
        assert_true(
            not os.path.exists(os.path.join(tmpdir, ".agents", "orca-audit.log")),
            "Source orca-audit.log should not be copied into freshly installed target",
        )
        assert_true(
            not os.path.exists(os.path.join(tmpdir, ".agents", "scripts", "__pycache__")),
            "Source __pycache__ should not be copied into freshly installed target",
        )

        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        assert_true(cfg.get("version") == "0.3.0-beta", f"Unexpected version: {cfg.get('version')}")
        assert_true(cfg.get("enableCarbon") is False, "Shared config must stay Pro-Safe (enableCarbon=False)")
        assert_true("SETUP.md" in cfg.get("exemptPathSubstrings", []), "SETUP.md must be exempt")
        assert_true(len(cfg.get("allowedWorkerModels", [])) > 0, "allowedWorkerModels must not be empty")

        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
        assert_true(state.get("setupCompleted") is False, "setupCompleted should be False before finalize")
        assert_true("installedAt" in state, "installedAt timestamp missing in .orca-state.json")

        with open(setup_md, "r", encoding="utf-8") as f:
            setup_content = f.read()
        assert_true("--finalize" in setup_content, "SETUP.md should include --finalize instruction")

        # Verify installed orca_hook.py works with the generated tailored config
        payload = {
            "conversationId": "boot-test-c1",
            "modelName": "gemini-3.8-flash-high",
            "toolCall": {
                "name": "swarm",
                "args": {"action": "add", "model": "auto", "brief": "Implement user auth feature and unit test"},
            },
        }
        proc = subprocess.run(
            [sys.executable, "-X", "utf8", hook_script],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=15,
        )
        assert_true(proc.returncode == 0, f"Bootstrapped orca_hook.py failed: {proc.stderr}")
        hook_res = json.loads(proc.stdout.strip())
        assert_true(hook_res.get("decision") == "allow", f"Expected allow from hook, got {hook_res}")
        expected_model = "gemini-4-neon-high" if cfg["environment"]["hasNeon"] else "gemini-4-hydrogen-high"
        assert_true(
            hook_res.get("overwrite", {}).get("model") == expected_model,
            f"Expected {expected_model}, got {hook_res}",
        )

        # Verify coordinator edit to SETUP.md is allowed while source file edit is blocked
        setup_edit_payload = {
            "conversationId": "boot-test-c1",
            "modelName": "gemini-3.8-flash-high",
            "toolCall": {"name": "edit_file", "args": {"Path": setup_md}},
        }
        proc2 = subprocess.run(
            [sys.executable, "-X", "utf8", hook_script],
            input=json.dumps(setup_edit_payload),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=15,
        )
        assert_true(json.loads(proc2.stdout.strip()).get("decision") == "allow", "SETUP.md edit should be allowed")

        # Run --finalize on the bootstrapped project
        target_bootstrap = os.path.join(tmpdir, ".agents", "scripts", "bootstrap.py")
        f_code, f_out, f_err = run_cmd(
            [sys.executable, "-X", "utf8", target_bootstrap, "--finalize", "--target", tmpdir]
        )
        assert_true(f_code == 0, f"bootstrap --finalize failed: {f_err}")
        assert_true(not os.path.exists(setup_md), "SETUP.md should be deleted after --finalize")
        assert_true("Setup finalized successfully" in f_out, f"Missing finalize banner: {f_out}")

        with open(state_path, "r", encoding="utf-8") as f:
            final_state = json.load(f)
        assert_true(final_state.get("setupCompleted") is True, "setupCompleted should be True after finalize")
        assert_true("finalizedAt" in final_state, "finalizedAt timestamp missing after finalize")

        # Idempotent second --finalize call should also succeed cleanly
        f_code2, _, f_err2 = run_cmd(
            [sys.executable, "-X", "utf8", target_bootstrap, "--finalize", "--target", tmpdir]
        )
        assert_true(f_code2 == 0, f"Second --finalize failed: {f_err2}")


def test_install_bat_preserves_existing_gemini_md():
    """Verify install.bat does not overwrite an existing GEMINI.md in target."""
    with tempfile.TemporaryDirectory(prefix="gemineone_preserve_") as tmpdir:
        gemini_md = os.path.join(tmpdir, "GEMINI.md")
        sentinel = "# Custom Project Rules\nDO_NOT_OVERWRITE\n"
        with open(gemini_md, "w", encoding="utf-8") as f:
            f.write(sentinel)

        code, out, err = run_cmd(["cmd", "/c", INSTALL_BAT, tmpdir])
        assert_true(code == 0, f"install.bat failed: stdout={out}\nstderr={err}")
        assert_true("preserving existing file" in out, f"Expected preservation message in stdout: {out}")

        with open(gemini_md, "r", encoding="utf-8") as f:
            content = f.read()
        assert_true(content == sentinel, "Existing GEMINI.md was unexpectedly overwritten")


def test_direct_probe_and_finalize():
    """Verify direct bootstrap.py --probe-and-configure and --finalize CLI flags."""
    with tempfile.TemporaryDirectory(prefix="gemineone_cli_") as tmpdir:
        code, out, err = run_cmd(
            [sys.executable, "-X", "utf8", BOOTSTRAP_SCRIPT, "--probe-and-configure", "--target", tmpdir]
        )
        assert_true(code == 0, f"Direct probe failed: {err}")
        assert_true("Probing environment for target:" in out, f"Unexpected probe output: {out}")
        assert_true(os.path.exists(os.path.join(tmpdir, "SETUP.md")), "SETUP.md not created")
        assert_true(os.path.exists(os.path.join(tmpdir, ".agents", "orca-config.json")), "orca-config.json not created")
        assert_true(os.path.exists(os.path.join(tmpdir, ".agents", ".orca-state.json")), ".orca-state.json not created")

        code2, _, err2 = run_cmd(
            [sys.executable, "-X", "utf8", BOOTSTRAP_SCRIPT, "--finalize", "--target", tmpdir]
        )
        assert_true(code2 == 0, f"Direct finalize failed: {err2}")
        assert_true(not os.path.exists(os.path.join(tmpdir, "SETUP.md")), "SETUP.md not removed")


def test_offline_fallback_config():
    """Verify generate_tailored_config falls back safely when no live models are detected."""
    with tempfile.TemporaryDirectory(prefix="gemineone_offline_") as tmpdir:
        env_info = {"antigravity": False, "cursor": True, "claude": False, "agy_cli_path": None}
        cfg, state = bootstrap.generate_tailored_config(tmpdir, {}, {}, [], env_info)

        assert_true(cfg["version"] == "0.3.0-beta", "Version mismatch in offline config")
        assert_true(cfg["environment"]["hasNeon"] is False, "hasNeon should be False offline")
        assert_true(cfg["environment"]["hasCarbon"] is False, "hasCarbon should be False offline")
        assert_true(cfg["defaultTier"] == "hydrogen-high", "Offline defaultTier should be hydrogen-high")
        assert_true(
            cfg["adaptiveEffort"]["defaultModel"] == "gemini-4-hydrogen-high",
            "Offline defaultModel should be gemini-4-hydrogen-high",
        )
        assert_true(len(cfg["allowedWorkerModels"]) > 0, "Offline allowedWorkerModels should use safe defaults")
        assert_true(state["setupCompleted"] is False, "Offline state setupCompleted should be False")


def main():
    tests = [
        ("install.bat E2E probe + hook integration + finalize", test_install_bat_end_to_end),
        ("install.bat preserves existing GEMINI.md", test_install_bat_preserves_existing_gemini_md),
        ("Direct bootstrap.py --probe-and-configure & --finalize", test_direct_probe_and_finalize),
        ("Offline fallback config generation", test_offline_fallback_config),
    ]

    print("=== gemineone 0.3.0-beta Bootstrap Test Suite ===")
    passed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"[PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {name}: {e}")
            sys.exit(1)

    print(f"\nAll {passed}/{len(tests)} bootstrap tests passed successfully!")


if __name__ == "__main__":
    main()
