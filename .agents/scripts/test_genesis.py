import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AGENTS_DIR = os.path.dirname(SCRIPT_DIR)
REPO_ROOT = os.path.dirname(AGENTS_DIR)
TEMPLATES_DIR = os.path.join(REPO_ROOT, "templates")

REQUIRED_TEMPLATES = {
    "GEMINI.md": os.path.join(TEMPLATES_DIR, "GEMINI.md"),
    ".cursorrules": os.path.join(TEMPLATES_DIR, ".cursorrules"),
    "CLAUDE.md": os.path.join(TEMPLATES_DIR, "CLAUDE.md"),
}
ROOT_GEMINI_MD = os.path.join(REPO_ROOT, "GEMINI.md")
REPO_URL = "https://github.com/mingjae1/gemineone.git"


def assert_true(cond, msg):
    if not cond:
        raise AssertionError(msg)


def _handle_remove_readonly(func, path, exc_info):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def rmtree_force(path):
    if os.path.exists(path):
        shutil.rmtree(path, onerror=_handle_remove_readonly)


def run_cmd(cmd, cwd=None, input_text=None, env=None, timeout=30):
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        input=input_text,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    return proc.returncode, proc.stdout, proc.stderr


def needs_genesis(workspace_dir):
    """Turn 1 Genesis check: returns True when .agents/scripts/orca_hook.py is missing."""
    hook_path = os.path.join(workspace_dir, ".agents", "scripts", "orca_hook.py")
    return not os.path.exists(hook_path)


def execute_genesis_assembly(workspace_dir, source_repo_url):
    """Simulates the Genesis Protocol clone/pull + .agents copy + cleanup steps."""
    tmp_dir = os.path.join(workspace_dir, ".gemineone-tmp")
    if os.path.isdir(os.path.join(tmp_dir, ".git")):
        code, out, err = run_cmd(["git", "-C", tmp_dir, "pull", "--ff-only"])
        assert_true(code == 0, f"git pull failed: stdout={out}\nstderr={err}")
    else:
        code, out, err = run_cmd(
            ["git", "clone", "--depth", "1", source_repo_url, tmp_dir]
        )
        assert_true(code == 0, f"git clone failed: stdout={out}\nstderr={err}")

    src_agents = os.path.join(tmp_dir, ".agents")
    dst_agents = os.path.join(workspace_dir, ".agents")
    assert_true(os.path.isdir(src_agents), f"Missing .agents in cloned repo: {src_agents}")

    shutil.copytree(
        src_agents,
        dst_agents,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "orca-audit.log", ".orca-state.json"),
    )
    rmtree_force(tmp_dir)
    assert_true(not os.path.exists(tmp_dir), "Temporary .gemineone-tmp folder was not cleaned up")


def run_hook_in_workspace(workspace_dir, payload):
    hook_script = os.path.join(workspace_dir, ".agents", "scripts", "orca_hook.py")
    code, out, err = run_cmd(
        [sys.executable, "-X", "utf8", hook_script],
        cwd=workspace_dir,
        input_text=json.dumps(payload, ensure_ascii=False),
    )
    assert_true(code == 0, f"orca_hook.py failed (code={code}): {err}")
    return json.loads(out.strip())


def test_templates_and_protocol_markers():
    """Verify all Genesis templates and root GEMINI.md exist and contain required protocol rules."""
    assert_true(os.path.isdir(TEMPLATES_DIR), f"templates/ directory missing: {TEMPLATES_DIR}")

    for name, path in REQUIRED_TEMPLATES.items():
        assert_true(os.path.isfile(path), f"Template missing: {path}")
        with open(path, "r", encoding="utf-8-sig") as f:
            content = f.read()

        assert_true(".agents/scripts/orca_hook.py" in content, f"{name}: missing Turn 1 orca_hook.py check")
        assert_true(REPO_URL in content, f"{name}: missing gemineone repo URL ({REPO_URL})")
        assert_true("sync_models.py" in content, f"{name}: missing sync_models.py step")
        assert_true("1D" in content and "Fast Intake" in content, f"{name}: missing 1D Fast Intake rule")
        assert_true("Adaptive" in content, f"{name}: missing Adaptive Effort rule")
        assert_true("Parallel Fan-out" in content, f"{name}: missing Parallel Fan-out rule")
        assert_true("Production Orchestrator Rules" in content, f"{name}: missing Production Orchestrator section")

    assert_true(os.path.isfile(ROOT_GEMINI_MD), f"Root GEMINI.md missing: {ROOT_GEMINI_MD}")
    with open(ROOT_GEMINI_MD, "r", encoding="utf-8-sig") as f:
        root_content = f.read().replace("\r\n", "\n")
    with open(REQUIRED_TEMPLATES["GEMINI.md"], "r", encoding="utf-8-sig") as f:
        tpl_content = f.read().replace("\r\n", "\n")
    assert_true(
        root_content == tpl_content,
        "Root GEMINI.md must stay synchronized with templates/GEMINI.md",
    )


def test_genesis_fresh_mock_workspace():
    """Verify full Turn 1 Genesis flow in a fresh mock workspace with existing user files & git repo."""
    tmpdir = tempfile.mkdtemp(prefix="gemineone_genesis_fresh_")
    try:
        # 1. Simulate a user's existing project with its own git repo, source code, and dropped GEMINI.md
        shutil.copy2(REQUIRED_TEMPLATES["GEMINI.md"], os.path.join(tmpdir, "GEMINI.md"))
        src_dir = os.path.join(tmpdir, "src")
        os.makedirs(src_dir, exist_ok=True)
        app_py = os.path.join(src_dir, "app.py")
        user_code = 'print("user project intact")\n'
        with open(app_py, "w", encoding="utf-8") as f:
            f.write(user_code)

        g_code, _, g_err = run_cmd(["git", "init"], cwd=tmpdir)
        assert_true(g_code == 0, f"git init in mock workspace failed: {g_err}")

        # 2. Turn 1 check must detect missing .agents/scripts/orca_hook.py
        assert_true(needs_genesis(tmpdir) is True, "Fresh workspace should trigger Genesis Mode")

        # 3. Execute Genesis clone/copy/cleanup using local repo as deterministic git remote
        local_remote = "file:///" + REPO_ROOT.replace("\\", "/")
        execute_genesis_assembly(tmpdir, local_remote)

        assert_true(needs_genesis(tmpdir) is False, "orca_hook.py must exist after Genesis assembly")
        assert_true(
            not os.path.exists(os.path.join(tmpdir, ".agents", "orca-audit.log")),
            "Transient orca-audit.log should not be copied during Genesis",
        )
        assert_true(
            not os.path.exists(os.path.join(tmpdir, ".agents", "scripts", "__pycache__")),
            "Transient __pycache__ should not be copied during Genesis",
        )

        # 4. Run sync_models.py to auto-detect local models/capabilities
        sync_script = os.path.join(tmpdir, ".agents", "scripts", "sync_models.py")
        assert_true(os.path.isfile(sync_script), "sync_models.py missing after Genesis assembly")

        s_code, s_out, s_err = run_cmd([sys.executable, "-X", "utf8", sync_script], cwd=tmpdir)
        state_path = os.path.join(tmpdir, ".agents", ".orca-state.json")
        cfg_path = os.path.join(tmpdir, ".agents", "orca-config.json")

        if s_code == 0:
            # Live Antigravity API path verified
            assert_true("[API Sync] Successfully fetched" in s_out, f"Unexpected sync_models output: {s_out}")
            assert_true(os.path.isfile(state_path), ".orca-state.json not created by sync_models.py")
            with open(state_path, "r", encoding="utf-8") as f:
                state = json.load(f)
            assert_true(len(state.get("liveModels", {})) > 0, "liveModels should be populated by sync_models.py")
            assert_true(isinstance(state.get("hasCarbon"), bool), "hasCarbon bool missing in .orca-state.json")
            assert_true("lastSynced" in state, "lastSynced missing in .orca-state.json")
        else:
            # Fallback for non-Antigravity environments (no agy.exe installed)
            assert_true(
                "agy.exe not found" in s_err or "FileNotFoundError" in s_err,
                f"sync_models.py failed unexpectedly: stdout={s_out}\nstderr={s_err}",
            )
            boot_script = os.path.join(tmpdir, ".agents", "scripts", "bootstrap.py")
            b_code, _, b_err = run_cmd(
                [sys.executable, "-X", "utf8", boot_script, "--probe-and-configure", "--target", tmpdir],
                cwd=tmpdir,
            )
            assert_true(b_code == 0, f"Fallback bootstrap probe failed: {b_err}")
            f_code, _, f_err = run_cmd(
                [sys.executable, "-X", "utf8", boot_script, "--finalize", "--target", tmpdir],
                cwd=tmpdir,
            )
            assert_true(f_code == 0, f"Fallback bootstrap finalize failed: {f_err}")

        # 5. Verify user files and git repo are untouched, and Pro-Safe config is intact
        with open(app_py, "r", encoding="utf-8") as f:
            assert_true(f.read() == user_code, "User source file was altered during Genesis")
        assert_true(os.path.isdir(os.path.join(tmpdir, ".git")), "User .git directory was lost")

        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        assert_true(cfg.get("enableCarbon") is False, "Shared orca-config.json must remain Pro-Safe")
        assert_true(len(cfg.get("allowedWorkerModels", [])) > 0, "allowedWorkerModels must not be empty")

        # 6. Verify transition into Production Orchestrator Mode via installed orca_hook.py
        res_arch = run_hook_in_workspace(
            tmpdir,
            {
                "conversationId": "genesis-prod-1",
                "modelName": "gemini-3.8-flash-high",
                "toolCall": {
                    "name": "swarm",
                    "args": {
                        "action": "add",
                        "model": "auto",
                        "brief": "Design distributed concurrency architecture and deadlock guard",
                    },
                },
            },
        )
        assert_true(res_arch.get("decision") == "allow", f"Expected allow, got {res_arch}")
        assert_true(
            res_arch.get("overwrite", {}).get("model") == "gemini-4-argon-high",
            f"Expected gemini-4-argon-high, got {res_arch}",
        )

        res_docs = run_hook_in_workspace(
            tmpdir,
            {
                "conversationId": "genesis-prod-1",
                "modelName": "gemini-3.8-flash-high",
                "toolCall": {
                    "name": "swarm",
                    "args": {
                        "action": "add",
                        "model": "auto",
                        "brief": "Update README formatting and .gitignore docs",
                    },
                },
            },
        )
        assert_true(
            res_docs.get("overwrite", {}).get("model") == "gemini-3.8-flash-high",
            f"Expected gemini-3.8-flash-high, got {res_docs}",
        )

        # Coordinator direct source edit must be blocked while GEMINI.md remains exempt
        res_block = run_hook_in_workspace(
            tmpdir,
            {
                "conversationId": "genesis-prod-1",
                "modelName": "gemini-3.8-flash-high",
                "toolCall": {"name": "edit_file", "args": {"Path": app_py}},
            },
        )
        assert_true(res_block.get("decision") == "deny", f"Expected deny on src/app.py, got {res_block}")

        res_allow = run_hook_in_workspace(
            tmpdir,
            {
                "conversationId": "genesis-prod-1",
                "modelName": "gemini-3.8-flash-high",
                "toolCall": {"name": "edit_file", "args": {"Path": os.path.join(tmpdir, "GEMINI.md")}},
            },
        )
        assert_true(res_allow.get("decision") == "allow", f"Expected allow on GEMINI.md, got {res_allow}")
    finally:
        rmtree_force(tmpdir)


def test_genesis_pull_branch_and_production_skip():
    """Verify git pull path when .gemineone-tmp exists and Turn 2+ skip when already installed."""
    tmpdir = tempfile.mkdtemp(prefix="gemineone_genesis_pull_")
    try:
        local_remote = "file:///" + REPO_ROOT.replace("\\", "/")
        tmp_staging = os.path.join(tmpdir, ".gemineone-tmp")

        # Pre-seed .gemineone-tmp to exercise the `git -C .gemineone-tmp pull --ff-only` branch
        c_code, _, c_err = run_cmd(["git", "clone", "--depth", "1", local_remote, tmp_staging])
        assert_true(c_code == 0, f"Pre-seed clone failed: {c_err}")

        assert_true(needs_genesis(tmpdir) is True, "Workspace without .agents should require Genesis")
        execute_genesis_assembly(tmpdir, local_remote)
        assert_true(needs_genesis(tmpdir) is False, "Workspace should now be in Production Mode")

        # Turn 2+: Genesis must be skipped (no .gemineone-tmp recreated), hook runs immediately
        if needs_genesis(tmpdir):
            raise AssertionError("Turn 2 incorrectly re-triggered Genesis")

        assert_true(
            not os.path.exists(tmp_staging),
            "Turn 2 skip should never recreate .gemineone-tmp",
        )
        res = run_hook_in_workspace(
            tmpdir,
            {
                "conversationId": "genesis-turn2",
                "modelName": "gemini-3.8-flash-high",
                "toolCall": {
                    "name": "swarm",
                    "args": {"action": "add", "model": "neon-low", "brief": "Minor script edit"},
                },
            },
        )
        assert_true(
            res.get("overwrite", {}).get("model") == "gemini-4-neon-low",
            f"Expected explicit neon-low respected on Turn 2, got {res}",
        )
    finally:
        rmtree_force(tmpdir)


def test_cross_agent_templates_and_fallback():
    """Verify Cursor (.cursorrules) & Claude Code (CLAUDE.md) single-file Genesis + offline fallback."""
    local_remote = "file:///" + REPO_ROOT.replace("\\", "/")

    for tpl_name in (".cursorrules", "CLAUDE.md"):
        tmpdir = tempfile.mkdtemp(prefix=f"gemineone_{tpl_name.replace('.', '')}_")
        try:
            shutil.copy2(REQUIRED_TEMPLATES[tpl_name], os.path.join(tmpdir, tpl_name))
            assert_true(needs_genesis(tmpdir) is True, f"{tpl_name}: Turn 1 should trigger Genesis")

            execute_genesis_assembly(tmpdir, local_remote)
            assert_true(needs_genesis(tmpdir) is False, f"{tpl_name}: orca_hook.py missing after Genesis")

            # Test non-Antigravity host fallback (bootstrap probe + immediate finalize cleanup)
            boot_script = os.path.join(tmpdir, ".agents", "scripts", "bootstrap.py")
            b_code, _, b_err = run_cmd(
                [sys.executable, "-X", "utf8", boot_script, "--probe-and-configure", "--target", tmpdir],
                cwd=tmpdir,
            )
            assert_true(b_code == 0, f"{tpl_name}: fallback probe failed: {b_err}")

            f_code, _, f_err = run_cmd(
                [sys.executable, "-X", "utf8", boot_script, "--finalize", "--target", tmpdir],
                cwd=tmpdir,
            )
            assert_true(f_code == 0, f"{tpl_name}: fallback finalize failed: {f_err}")
            assert_true(
                not os.path.exists(os.path.join(tmpdir, "SETUP.md")),
                f"{tpl_name}: transient SETUP.md should be cleaned up after finalize",
            )

            with open(os.path.join(tmpdir, ".agents", ".orca-state.json"), "r", encoding="utf-8") as f:
                state = json.load(f)
            assert_true(state.get("setupCompleted") is True, f"{tpl_name}: setupCompleted should be True")
            assert_true(
                os.path.isfile(os.path.join(tmpdir, tpl_name)),
                f"{tpl_name}: original template file must remain intact",
            )
        finally:
            rmtree_force(tmpdir)


def main():
    tests = [
        ("Templates & Genesis Protocol markers + root GEMINI.md parity", test_templates_and_protocol_markers),
        ("Fresh mock workspace Genesis flow (clone + sync_models + prod hook)", test_genesis_fresh_mock_workspace),
        ("Staging git pull branch & Turn 2+ Production Mode skip", test_genesis_pull_branch_and_production_skip),
        ("Cross-agent templates (.cursorrules, CLAUDE.md) + fallback cleanup", test_cross_agent_templates_and_fallback),
    ]

    print("=== gemineone Iron Man Genesis Engine Test Suite ===")
    passed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"[PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {name}: {e}")
            sys.exit(1)

    print(f"\nAll {passed}/{len(tests)} genesis tests passed successfully!")


if __name__ == "__main__":
    main()
