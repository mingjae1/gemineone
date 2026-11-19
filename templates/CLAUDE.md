# CLAUDE.md - gemineone Agent Harness (Claude Code Genesis Edition)

## ⚡ Turn 1: Iron Man Single-Markdown Genesis Protocol (자가 조립 프로토콜)

> **Single-File Zero-Install Trigger**: Drop this `CLAUDE.md` file into any project root and start a Claude Code session. On Turn 1, the agent self-assembles the gemineone harness and syncs local capabilities automatically.

### Check (Turn 1 Mandatory Gate)
At the beginning of Turn 1, check whether `.agents/scripts/orca_hook.py` exists in the workspace root.

- **Case A — `.agents/scripts/orca_hook.py` already exists (Production Mode)**:
  - Skip Genesis bootstrap completely (zero overhead) and immediately enforce **Production Orchestrator Rules (0~5)** below.
- **Case B — `.agents/scripts/orca_hook.py` does NOT exist (Auto-Genesis Mode)**:
  1. Clone/pull `https://github.com/mingjae1/gemineone.git` into a temporary staging directory (`.gemineone-tmp`), copy `.agents/` into the workspace root without disturbing existing project files or `.git`, and remove `.gemineone-tmp`:

     **macOS / Linux / Git Bash**:
     ```bash
     if [ -d ".gemineone-tmp/.git" ]; then git -C .gemineone-tmp pull --ff-only; else git clone --depth 1 https://github.com/mingjae1/gemineone.git .gemineone-tmp; fi
     mkdir -p .agents && cp -R .gemineone-tmp/.agents/. .agents/ && rm -rf .agents/scripts/__pycache__ .agents/orca-audit.log .agents/.orca-state.json .gemineone-tmp
     ```

     **Windows (PowerShell)**:
     ```powershell
     if (Test-Path ".gemineone-tmp\.git") { git -C .gemineone-tmp pull --ff-only } else { git clone --depth 1 https://github.com/mingjae1/gemineone.git .gemineone-tmp }
     robocopy .gemineone-tmp\.agents .\.agents /E /XD __pycache__ /XF orca-audit.log .orca-state.json *.pyc | Out-Null
     Remove-Item -Recurse -Force .gemineone-tmp
     ```

  2. Auto-detect local models and environment capabilities via `sync_models.py`:
     ```bash
     python -X utf8 .agents/scripts/sync_models.py
     ```
     - If Antigravity CLI (`agy`) is not installed on this Claude Code host, gracefully fall back to environment probing & self-cleanup:
     ```bash
     python -X utf8 .agents/scripts/bootstrap.py --probe-and-configure --target .
     python -X utf8 .agents/scripts/bootstrap.py --finalize --target .
     ```
  3. Report Genesis completion concisely (1–2 lines) and immediately transition into **Production Orchestrator Rules** to fulfill the user's request.

---

# Production Orchestrator Rules (Claude Code)

## 0. Evidence Before Claims
- Back factual claims with concrete sources: `path:line`, exact command & output, or URL.
- Label claims: **Verified** (read/run this session), **Inferred** (state evidence), **Unknown**. Never fabricate test results or metrics.

## 1. Disciplined Execution & Surgical Changes
- Touch only requested code. No speculative features, abstractions, or unrequested refactoring.
- Match existing conventions. Clean up unused imports/variables. State assumptions upfront if ambiguous.
- Verification loop: **State plan -> Implement -> Verify (build/test) -> Report**.

## 2. 1D Fast Intake (Direct Coordinator Response)
- Reply directly and quickly to simple queries/intake without slow speculative directory sweeps or multi-file reads.
- When deep codebase exploration or architectural trade-off analysis is needed, delegate inspection to a dedicated subagent (`Agent` / `Task` tool) instead of blocking the main intake loop.

## 3. Adaptive Effort Routing & Subagent Delegation (적응형 노력치)
- Match reasoning effort and subagent model selection to task complexity per `.agents/orca-config.json` to conserve quota while maximizing quality:
  1. **Explicit Request Respected**: Honor user-requested effort tiers (`low`, `medium`, `high`, `xhigh`) or explicit model IDs without forcibly overriding them.
  2. **Adaptive Complexity Tiers** (aligned with `.agents/scripts/orca_hook.py`):
     - `deep_architecture_concurrency` (concurrency, deadlocks, distributed systems, RMI, deep architecture): Maximum reasoning tier (`gemini-4-argon-high` / `gemini-4-carbon` when enabled, or Opus-class reasoning in Claude Code)
     - `complex_implementation_debug` (multi-module implementation, benchmarks, full test suites, complex debugging): Extra-high tier (`gemini-4-neon-xhigh` / `gemini-4-hydrogen-xhigh`)
     - `standard_development_test` (feature implementation, components, APIs, unit tests — Default): High tier (`gemini-4-neon-high` / `gemini-4-hydrogen-high`)
     - `light_scripting_edit` (minor edits, renames, small scripts): Low tier (`gemini-4-neon-low` / `gemini-4-hydrogen-low`)
     - `boilerplate_config_docs` (`.gitignore`, README, formatting, comments, docs): Fast tier (`gemini-3.8-flash-high` / Haiku-class fast execution)
  3. **Pro-Safe Isolation**: Keep shared `.agents/orca-config.json` Pro-Safe (`enableCarbon: false`, `carbonFallback`: `gemini-4-argon-high`) and isolate local host capabilities in gitignored `.agents/.orca-state.json`.

## 4. Parallel Fan-out for Independent Tasks
- When multiple tasks have no sequential dependencies (e.g., independent modules, test suites, or disjoint bug fixes), never execute them one by one.
- Spawn multiple subagents in parallel in a single turn with disjoint file ownership (or isolated git worktrees when edits/builds could collide).

## 5. Git & Verification Loop
- Push Policy: Do NOT push on every minor test/edit. Confirm with the user on major milestones before running `git push`.
- Never run `git reset --hard` or `git clean` without explicit user confirmation.
