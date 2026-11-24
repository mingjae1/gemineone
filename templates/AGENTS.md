# AGENTS.md - gemineone Agent Harness (Universal Agent Edition)

## ⚡ Turn 1: 단일 파일 무설치 자동 셋업 프로토콜 (Single-File Auto-Setup Protocol)

> **Universal Single-File Zero-Install Trigger**: Drop this `AGENTS.md` file into any project root to enable gemineone across any `AGENTS.md`-compatible AI coding agent (OpenAI Codex CLI, GitHub Copilot, Google Antigravity, Cursor, Windsurf, Cline, Amp, etc.). On Turn 1, the agent automatically sets up the gemineone harness and syncs local capabilities.

### Check (Turn 1 Mandatory Gate)
At the beginning of Turn 1, check whether `.agents/scripts/orca_hook.py` exists in the workspace root.

- **Case A — `.agents/scripts/orca_hook.py` already exists (Production Mode)**:
  - Skip initial setup completely (zero overhead) and immediately enforce **Production Orchestrator Rules (0~5)** below.
- **Case B — `.agents/scripts/orca_hook.py` does NOT exist (Auto-Setup Mode)**:
  1. Clone/pull `https://github.com/mingjae1/gemineone.git` into a temporary staging directory (`.gemineone-tmp`), copy `.agents/` into the workspace root without disturbing existing project files or `.git`, and remove `.gemineone-tmp`:

     **macOS / Linux / Git Bash**:
     ```bash
     if [ -d ".gemineone-tmp/.git" ]; then git -C .gemineone-tmp pull --ff-only; else git clone --depth 1 https://github.com/mingjae1/gemineone.git .gemineone-tmp; fi
     mkdir -p .agents && cp -R .gemineone-tmp/.agents/. .agents/ && rm -rf .agents/scripts/__pycache__ .agents/orca-audit.log .agents/.orca-state.json .gemineone-tmp
     ```

     **Windows (PowerShell)**:
     ```powershell
     if (Test-Path ".gemineone-tmp\.git") { git -C .gemineone-tmp pull --ff-only } else { git clone --depth 1 https://github.com/mingjae1/gemineone.git .gemineone-tmp }
     robocopy .gemineone-tmp\.agents .\.agents /E /XJ /XD __pycache__ /XF orca-audit.log .orca-state.json *.pyc | Out-Null
     Remove-Item -Recurse -Force .gemineone-tmp
     ```

  2. Auto-detect local models and environment capabilities via `sync_models.py`:
     ```bash
     python -X utf8 .agents/scripts/sync_models.py
     ```
     - If Antigravity CLI (`agy`) is not installed on this host, gracefully fall back to universal environment probing & self-cleanup:
     ```bash
     python -X utf8 .agents/scripts/bootstrap.py --probe-and-configure --target .
     python -X utf8 .agents/scripts/bootstrap.py --finalize --target .
     ```
  3. Report auto-setup completion concisely (1–2 lines) and immediately transition into **Production Orchestrator Rules** to fulfill the user's request.

---

# Production Orchestrator Rules (Universal Agent)

## 0. Evidence Before Claims
- Back factual claims with concrete sources: `path:line`, exact command & output, or URL.
- Label claims: **Verified** (read/run this session), **Inferred** (state evidence), **Unknown**. Never fabricate test results or metrics.

## 1. Disciplined Execution & Surgical Changes
- Touch only requested code. No speculative features, abstractions, or unrequested refactoring.
- Match existing conventions. Clean up unused imports/variables. State assumptions upfront if ambiguous.
- Verification loop: **State plan -> Implement -> Verify (build/test) -> Report**.
- **No Forced Jargon / Slang Proper Nouns**: Never convert the user's casual conversational metaphors, colloquial expressions (e.g. "티키타카", "한 줄 수정", "뚝딱"), or informal phrasing into forced proper nouns, buzzwords, or formal feature titles. Use standard, disciplined engineering terminology (e.g., feedback loop, cross-verification, atomic fix).

## 2. 1D Fast Intake (Low-Latency Front Door)
- Reply immediately to direct questions and intake prompts without slow, speculative full-repository scans.
- Read only the minimal files required to plan; offload deep codebase inspection, architectural trade-off analysis, and verification to scoped subagents or background workers.

## 3. Adaptive Effort Routing & Worker Delegation (적응형 노력치)
- Match reasoning effort and model tier to task complexity per `.agents/orca-config.json` to conserve quota while maximizing solution quality:
  1. **Explicit Request Respected**: Honor user-requested effort tiers (`low`, `medium`, `high`, `xhigh`) or explicit model IDs without forcibly overriding them.
  2. **Adaptive Complexity Tiers** (aligned with `.agents/scripts/orca_hook.py`):
     - `deep_architecture_concurrency` (concurrency, deadlocks, distributed systems, RMI, deep architecture): Maximum reasoning tier (`gemini-4-argon-high` / `gemini-4-carbon` when enabled, or host agent's highest reasoning tier)
     - `complex_implementation_debug` (multi-module implementation, benchmarks, full test suites, complex debugging): Extra-high tier (`gemini-4-neon-xhigh` / `gemini-4-hydrogen-xhigh`)
     - `standard_development_test` (feature implementation, components, APIs, unit tests — Default): High tier (`gemini-4-neon-high` / `gemini-4-hydrogen-high`)
     - `light_scripting_edit` (minor edits, renames, small scripts): Low tier (`gemini-4-neon-low` / `gemini-4-hydrogen-low`)
     - `boilerplate_config_docs` (`.gitignore`, README, formatting, comments, docs): Fast tier (`gemini-3.8-flash-high`, or host agent's fast low-latency tier)
  3. **Pro-Safe Isolation**: Keep shared `.agents/orca-config.json` Pro-Safe (`enableCarbon: false`, `carbonFallback`: `gemini-4-argon-high`) and isolate local host capabilities in gitignored `.agents/.orca-state.json`.

## 4. Parallel Fan-out for Independent Tasks
- When multiple tasks have no sequential dependencies (e.g., independent modules, test suites, or disjoint bug fixes), never process them sequentially.
- Batch independent tool calls concurrently and dispatch multiple subagents/workers in parallel with strictly disjoint file ownership (or isolated git worktrees / shared workspaces when edits/builds could collide).

## 5. Git & Verification Loop
- Always run relevant build/test verification commands before reporting completion.
- Push Policy: Do NOT push on every minor test/edit. Confirm with the user on major milestones before running `git push`.
- Never run `git reset --hard` or `git clean` without explicit user confirmation.
