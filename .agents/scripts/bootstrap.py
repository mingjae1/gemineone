import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys

try:
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_agy_path():
    which_path = shutil.which("agy")
    if which_path and os.path.exists(which_path):
        return which_path
    user_home = os.environ.get("USERPROFILE", os.path.expanduser("~"))
    standard_path = os.path.join(user_home, ".gemini", "bin", "agy.exe")
    return standard_path


AGY_EXE = get_agy_path()

DEFAULT_ALLOWED_MODELS = [
    "gemini-3.8-flash-high",
    "gemini-3.8-flash-low",
    "gemini-3.8-flash-medium",
    "gemini-4-argon-high",
    "gemini-4-argon-low",
    "gemini-4-argon-medium",
    "gemini-4-carbon",
    "gemini-4-carbon-high",
    "gemini-4-carbon-low",
    "gemini-4-carbon-medium",
    "gemini-4-carbon-xhigh",
    "gemini-4-hydrogen-high",
    "gemini-4-hydrogen-low",
    "gemini-4-hydrogen-medium",
    "gemini-4-hydrogen-xhigh",
    "gemini-4-neon-high",
    "gemini-4-neon-low",
    "gemini-4-neon-medium",
    "gemini-4-neon-xhigh",
]


def run_command(cmd, timeout=10):
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except Exception as e:
        return -1, "", str(e)


def detect_host_environment(target_dir):
    """Detects available AI coding agent environments on this system."""
    env_info = {
        "antigravity": False,
        "cursor": False,
        "claude": False,
        "agy_cli_path": None,
    }

    if os.path.exists(AGY_EXE):
        env_info["antigravity"] = True
        env_info["agy_cli_path"] = AGY_EXE

    # Check for Cursor configs
    home = os.path.expanduser("~")
    cursor_dir = os.path.join(home, ".cursor")
    if os.path.exists(cursor_dir) or os.path.exists(os.path.join(target_dir, ".cursor")):
        env_info["cursor"] = True

    # Check for Claude Code configs
    claude_dir = os.path.join(home, ".claude")
    if os.path.exists(claude_dir):
        env_info["claude"] = True

    return env_info


def probe_live_models():
    """Queries live available models directly from Google Antigravity backend API."""
    if not os.path.exists(AGY_EXE):
        return {}

    code, stdout, _ = run_command([AGY_EXE, "models"])
    if code != 0:
        return {}

    models = {}
    for line in stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("Fetching"):
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            model_id = parts[0].strip()
            display_name = parts[1].strip()
            models[model_id] = display_name
        elif len(parts) == 1:
            models[parts[0].strip()] = parts[0].strip()

    return models


def probe_mcp_servers():
    """Probes connected MCP servers across Antigravity, Cursor, and Claude."""
    mcp_servers = {}

    # 1. Antigravity MCP
    if os.path.exists(AGY_EXE):
        code, stdout, _ = run_command([AGY_EXE, "mcp", "list"])
        if code == 0 and "No MCP servers" not in stdout:
            for line in stdout.splitlines():
                if line.strip():
                    mcp_servers[f"agy:{line.strip()}"] = {"source": "antigravity"}

    # 2. Cursor MCP
    home = os.path.expanduser("~")
    cursor_mcp = os.path.join(home, ".cursor", "mcp.json")
    if os.path.exists(cursor_mcp):
        try:
            with open(cursor_mcp, "r", encoding="utf-8") as f:
                data = json.load(f)
                for name, srv in data.get("mcpServers", {}).items():
                    mcp_servers[f"cursor:{name}"] = {"source": "cursor", "config": srv}
        except Exception:
            pass

    return mcp_servers


def probe_plugins():
    """Probes installed Antigravity plugins."""
    plugins = []
    if os.path.exists(AGY_EXE):
        code, stdout, _ = run_command([AGY_EXE, "plugin", "list"])
        if code == 0 and "No plugins" not in stdout:
            for line in stdout.splitlines():
                if line.strip():
                    plugins.append(line.strip())
    return plugins


def generate_tailored_config(target_dir, models, mcp_servers, plugins, env_info):
    """Generates customized orca-config.json for target project environment."""
    config_path = os.path.join(target_dir, ".agents", "orca-config.json")
    state_path = os.path.join(target_dir, ".agents", ".orca-state.json")

    has_carbon = any("carbon" in m.lower() for m in models.keys())
    has_neon = any("neon" in m.lower() for m in models.keys())

    # Build safe base config
    cfg = {
        "version": "0.3.0-beta",
        "enabled": True,
        "enforceWorkerForEdits": True,
        "enableCarbon": False,  # Pro-safe default in shared config
        "carbonFallback": "gemini-4-argon-high",
        "defaultTier": "neon-high" if has_neon else "hydrogen-high",
        "environment": {
            "antigravity": env_info["antigravity"],
            "cursor": env_info["cursor"],
            "claude": env_info["claude"],
            "hasNeon": has_neon,
            "hasCarbon": has_carbon,
        },
        "adaptiveEffort": {
            "enabled": True,
            "defaultModel": "gemini-4-neon-high" if has_neon else "gemini-4-hydrogen-high",
            "rules": [
                {
                    "name": "deep_architecture_concurrency",
                    "targetModel": "gemini-4-argon-high",
                    "keywords": [
                        "architect", "concurrency", "race condition", "deadlock", "distributed",
                        "rmi", "memory leak", "escalate", "stubborn", "synchronization",
                        "동시성", "분산", "아키텍처", "데드락", "경합", "메모리 누수", "에스컬레이션", "심층", "설계"
                    ]
                },
                {
                    "name": "complex_implementation_debug",
                    "targetModel": "gemini-4-neon-xhigh" if has_neon else "gemini-4-hydrogen-xhigh",
                    "keywords": [
                        "complex", "heavy", "benchmark", "full test suite", "multi-module",
                        "심층 분석", "복합", "대규모", "전체 테스트", "까다로운"
                    ]
                },
                {
                    "name": "boilerplate_config_docs",
                    "targetModel": "gemini-3.8-flash-high",
                    "keywords": [
                        "gitignore", "readme", "format", "formatting", "typo", "boilerplate",
                        "cleanup", "lint", "comment", "docs", "documentation", "trivial",
                        "단순", "오타", "문서", "포맷", "설정", "정리", "주석", "보일러플레이트"
                    ]
                },
                {
                    "name": "light_scripting_edit",
                    "targetModel": "gemini-4-neon-low" if has_neon else "gemini-4-hydrogen-low",
                    "keywords": [
                        "light", "script", "rename", "minor", "경량", "수정", "단순 스크립트", "이름 변경"
                    ]
                },
                {
                    "name": "standard_development_test",
                    "targetModel": "gemini-4-neon-high" if has_neon else "gemini-4-hydrogen-high",
                    "keywords": [
                        "implement", "feature", "build", "test", "component", "refactor",
                        "api", "구현", "기능", "컴포넌트", "빌드", "테스트", "리팩토링"
                    ]
                }
            ]
        },
        "tiers": {
            "flash": "gemini-3.8-flash-high",
            "flash-low": "gemini-3.8-flash-low",
            "flash-medium": "gemini-3.8-flash-medium",
            "flash-high": "gemini-3.8-flash-high",
            "hydrogen": "gemini-4-hydrogen-high",
            "hydrogen-low": "gemini-4-hydrogen-low",
            "hydrogen-medium": "gemini-4-hydrogen-medium",
            "hydrogen-high": "gemini-4-hydrogen-high",
            "hydrogen-xhigh": "gemini-4-hydrogen-xhigh",
            "neon": "gemini-4-neon-high",
            "neon-low": "gemini-4-neon-low",
            "neon-medium": "gemini-4-neon-medium",
            "neon-high": "gemini-4-neon-high",
            "neon-xhigh": "gemini-4-neon-xhigh",
            "argon": "gemini-4-argon-high",
            "argon-low": "gemini-4-argon-low",
            "argon-medium": "gemini-4-argon-medium",
            "argon-high": "gemini-4-argon-high",
            "carbon": "gemini-4-carbon",
            "carbon-low": "gemini-4-carbon-low",
            "carbon-medium": "gemini-4-carbon-medium",
            "carbon-high": "gemini-4-carbon",
            "carbon-xhigh": "gemini-4-carbon-xhigh",
            "low": "gemini-4-neon-low" if has_neon else "gemini-4-hydrogen-low",
            "medium": "gemini-4-neon-medium" if has_neon else "gemini-4-hydrogen-medium",
            "high": "gemini-4-neon-high" if has_neon else "gemini-4-hydrogen-high",
            "xhigh": "gemini-4-neon-xhigh" if has_neon else "gemini-4-hydrogen-xhigh",
        },
        "allowedWorkerModels": sorted(list(models.keys())) if models else list(DEFAULT_ALLOWED_MODELS),
        "mcpServers": mcp_servers,
        "plugins": plugins,
        "exemptPathSubstrings": [
            ".agents",
            ".gemini",
            "antigravity\\brain",
            "antigravity/brain",
            "GEMINI.md",
            "README.md",
            "CHANGELOG.md",
            "SETUP.md"
        ]
    }

    os.makedirs(os.path.join(target_dir, ".agents"), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

    # Local state (gitignored)
    local_state = {
        "liveModels": models,
        "hasCarbon": has_carbon,
        "hasNeon": has_neon,
        "mcpServers": mcp_servers,
        "plugins": plugins,
        "setupCompleted": False,
        "installedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(local_state, f, indent=2, ensure_ascii=False)

    return cfg, local_state


def write_transient_setup_prompt(target_dir, cfg, local_state):
    """Writes temporary SETUP.md to guide the first AI session."""
    setup_file = os.path.join(target_dir, "SETUP.md")
    content = f"""# 🛠️ gemineone Setup Agent (셋업 단계)

이 프로젝트는 현재 **gemineone 자가 부트스트랩 셋업 단계**에 있습니다.

---

### 🔍 자동 감지된 환경 진단 결과
* **가용 AI 에이전트 환경**: Antigravity={cfg['environment']['antigravity']}, Cursor={cfg['environment']['cursor']}, Claude={cfg['environment']['claude']}
* **감지된 실시간 모델 수**: {len(local_state['liveModels'])}개 모델 가용
  - 최신 Neon 패밀리 지원: **{cfg['environment']['hasNeon']}**
  - Ultra Carbon 접근 권한: **{cfg['environment']['hasCarbon']}**
* **연결된 MCP 서버**: {len(local_state['mcpServers'])}개 감지
* **활성 플러그인**: {len(local_state['plugins'])}개 감지

---

### 📋 셋업 완료 절차
1. 사용자에게 감지된 모델 및 MCP 환경 요약을 보고합니다.
2. 사용자가 셋업 확정을 원할 때 다음 명령어를 실행하여 **셋업용 설정들을 자가 청소(Self-Cleanup)**하고 본 운영 모드로 전환합니다:

```cmd
python -X utf8 .agents/scripts/bootstrap.py --finalize --target .
```

실행 후 이 `SETUP.md` 파일은 자동으로 영구 제거되며, 최적화된 오케스트레이션 시스템만 남습니다.
"""
    with open(setup_file, "w", encoding="utf-8") as f:
        f.write(content)


def finalize_setup(target_dir):
    """Cleans up setup-only files and leaves only the lean production orchestration system."""
    setup_file = os.path.join(target_dir, "SETUP.md")
    if os.path.exists(setup_file):
        os.remove(setup_file)
        print(f"[Cleanup] Removed transient setup guide: {setup_file}")

    state_path = os.path.join(target_dir, ".agents", ".orca-state.json")
    if os.path.exists(state_path):
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                state = json.load(f)
            state["setupCompleted"] = True
            state["finalizedAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            print("[Cleanup] Marked setup as completed in .orca-state.json")
        except Exception:
            pass

    print("[gemineone] Setup finalized successfully! Clean orchestration harness is now active.")


def main():
    parser = argparse.ArgumentParser(description="gemineone Self-Bootstrapping Setup Engine")
    parser.add_argument("--target", default=".", help="Target project directory")
    parser.add_argument("--probe-and-configure", action="store_true", help="Probe host environment and generate tailored config")
    parser.add_argument("--finalize", action="store_true", help="Complete setup and cleanup transient setup files")
    args = parser.parse_args()

    target_dir = os.path.abspath(args.target)

    if args.finalize:
        finalize_setup(target_dir)
        return

    if args.probe_and_configure or len(sys.argv) == 1:
        print(f"[gemineone] Probing environment for target: {target_dir}")
        env_info = detect_host_environment(target_dir)
        models = probe_live_models()
        mcp_servers = probe_mcp_servers()
        plugins = probe_plugins()

        print(f"  - Antigravity detected: {env_info['antigravity']}")
        print(f"  - Cursor detected: {env_info['cursor']}")
        print(f"  - Live models fetched: {len(models)}")
        print(f"  - Connected MCP servers: {len(mcp_servers)}")

        cfg, local_state = generate_tailored_config(target_dir, models, mcp_servers, plugins, env_info)
        write_transient_setup_prompt(target_dir, cfg, local_state)

        print("[gemineone] Phase 1 bootstrap complete! SETUP.md created.")


if __name__ == "__main__":
    main()
