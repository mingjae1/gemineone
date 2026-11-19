# GEMINI.md - gemineone Agent Harness (Iron Man Genesis Edition)

## ⚡ Turn 1: Iron Man Single-Markdown Genesis Protocol (자가 조립 프로토콜)

> **Single-File Zero-Install Trigger**: 이 파일 하나만 프로젝트 루트에 두고 대화를 시작하면, 에이전트가 스스로 하네스를 조립하고 로컬 모델 환경을 동기화합니다.

### Check (Turn 1 최우선 확인)
대화 시작(Turn 1) 시 워크스페이스 루트에 `.agents/scripts/orca_hook.py` 파일이 존재하는지 확인합니다.

- **Case A — `.agents/scripts/orca_hook.py`가 이미 존재하는 경우 (Production Mode)**:
  - Genesis 부트스트랩을 **완전히 생략**하고, 지연 없이 아래 **Production Orchestrator Rules (0~5)**를 즉시 적용합니다.
- **Case B — `.agents/scripts/orca_hook.py`가 존재하지 않는 경우 (Auto-Genesis Mode)**:
  1. 아래 명령으로 `https://github.com/mingjae1/gemineone.git`에서 최신 하네스를 임시 폴더(`.gemineone-tmp`)로 클론/풀하고 `.agents/`만 현재 프로젝트로 복사한 뒤 임시 폴더를 즉시 정리합니다 (기존 프로젝트 파일과 `.git` 보존):

     **Windows (PowerShell)**:
     ```powershell
     if (Test-Path ".gemineone-tmp\.git") { git -C .gemineone-tmp pull --ff-only } else { git clone --depth 1 https://github.com/mingjae1/gemineone.git .gemineone-tmp }
     robocopy .gemineone-tmp\.agents .\.agents /E /XD __pycache__ /XF orca-audit.log .orca-state.json *.pyc | Out-Null
     Remove-Item -Recurse -Force .gemineone-tmp
     ```

     **macOS / Linux (Bash)**:
     ```bash
     if [ -d ".gemineone-tmp/.git" ]; then git -C .gemineone-tmp pull --ff-only; else git clone --depth 1 https://github.com/mingjae1/gemineone.git .gemineone-tmp; fi
     mkdir -p .agents && cp -R .gemineone-tmp/.agents/. .agents/ && rm -rf .agents/scripts/__pycache__ .agents/orca-audit.log .agents/.orca-state.json .gemineone-tmp
     ```

  2. 로컬 계정 가용 모델 및 기능(Neon/Carbon 등)을 실시간 자동 감지하여 `.agents/orca-config.json`과 로컬 격리 `.agents/.orca-state.json`에 동기화합니다:
     ```bash
     python -X utf8 .agents/scripts/sync_models.py
     ```
     *(만약 `agy` CLI가 없는 오프라인/비-Antigravity 환경이라면 `python -X utf8 .agents/scripts/bootstrap.py --probe-and-configure --target . && python -X utf8 .agents/scripts/bootstrap.py --finalize --target .`로 Pro-Safe 기본 구성을 생성합니다.)*
  3. 조립 완료 및 감지된 모델 요약을 1~2줄로 간단히 보고한 뒤, **즉시 아래 Production Orchestrator Rules로 전환**하여 사용자의 본래 요청을 처리합니다.

---

# Production Orchestrator Rules (Antigravity)

## 0. Evidence Before Claims
- Back factual claims with source: `path:line`, exact command & output, or URL.
- Label claims: **Verified** (read/run this session), **Inferred** (state evidence), **Unknown**. Never guess or invent numbers.

## 1. Disciplined Execution & Surgical Changes
- Touch only requested code. No speculative features, abstractions, or unrequested refactoring.
- Match existing conventions. Clean up unused imports/variables. State assumptions upfront if ambiguous.
- Verification loop: State plan -> Implement -> Verify (build/test) -> Report.

## 2. 1D Direct Chat & Fast Intake (`gemini-3.8-flash-high`)
- All direct user conversations run on `gemini-3.8-flash-high` as the coordinator.
- Do NOT run slow exploratory file scans or multi-file reads before answering initial user commands.
- Reply immediately for simple queries/intake. When codebase inspection is needed to craft architectural choices or `ask_question` options, delegate analysis to a Swarm worker.

## 3. Adaptive Thinking Effort Swarm Workers (적응형 노력치)
- Thinking effort tiers are adaptive across the Gemini family (Flash, Hydrogen, Neon, Argon) to prevent quota exhaustion and balance reasoning power:
  1. **Explicit Request Respected**: When a specific tier (`low`, `medium`, `high`, `xhigh`) or explicit model ID is requested, the hook respects the requested tier instead of forcibly upgrading to max effort.
  2. **Adaptive Auto-Routing**: When `model` is omitted or set to `auto`, `.agents/scripts/orca_hook.py` inspects the task `brief` and keywords:
     - `deep_architecture_concurrency` (동시성/데드락/분산/RMI/심층 아키텍처): `gemini-4-argon-high` (또는 `enableCarbon: true` 시 `gemini-4-carbon`)
     - `complex_implementation_debug` (대규모/벤치마크/복합 디버깅): `gemini-4-hydrogen-xhigh` 또는 `gemini-4-neon-xhigh`
     - `standard_development_test` (기능 구현/컴포넌트/테스트): `gemini-4-hydrogen-high` (Default) 또는 `gemini-4-neon-high`
     - `light_scripting_edit` (경량 스크립트/단순 수정): `gemini-4-hydrogen-low` 또는 `gemini-4-neon-low`
     - `boilerplate_config_docs` (단순 설정/.gitignore/README/포맷팅): `gemini-3.8-flash-high`
  3. **Neon & Carbon 지원 (최신 릴리즈 및 미래 호환성)**:
     - Antigravity 1.5.12 패치로 추가된 **`gemini-4-neon` 패밀리(Low~XHigh, Orchestrator)** 전 티어 완벽 지원.
     - `gemini-4-carbon` 패밀리 사전 등록 및 Graceful Fallback 지원 (`carbonFallback`: `gemini-4-argon-high`).
- `.agents/hooks.json` automatically blocks coordinator direct file edits outside exempt paths and transparently routes swarm workers to the appropriate adaptive model tier.

## 4. Parallel Fan-out for Independent Tasks
- When multiple tasks exist without sequential dependencies (e.g. independent components, tests, or bug fixes across different files), never process them sequentially with a single worker.
- Dispatch multiple Swarm workers in parallel in a single turn with disjoint file/module ownership (or `workspace: "share"` if artifacts collide) to execute concurrently.

## 5. Git & Verification Loop
- Push Policy: Do NOT push on every minor test/edit. On major milestones, confirm with user before running `git push`.
- Never run `git reset --hard` or `git clean` without asking.
