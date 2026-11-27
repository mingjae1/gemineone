# GEMINI.md - gemineone Agent Harness

## ⚡ Turn 1: 단일 파일 무설치 자동 셋업 프로토콜 (Single-File Auto-Setup Protocol)

> **Single-File Zero-Install Trigger**: 이 파일 하나만 프로젝트 루트에 두고 대화를 시작하면, 에이전트가 스스로 하네스를 구성하고 로컬 모델 환경을 동기화합니다.

### Check (Turn 1 최우선 확인)
대화 시작(Turn 1) 시 워크스페이스 루트에 `.agents/scripts/orca_hook.py` 파일이 존재하는지 확인합니다.

- **Case A — `.agents/scripts/orca_hook.py`가 이미 존재하는 경우 (Production Mode)**:
  - 초기 설정을 **완전히 생략**하고, 지연 없이 아래 **Production Orchestrator Rules (0~5)**를 즉시 적용합니다.
- **Case B — `.agents/scripts/orca_hook.py`가 존재하지 않는 경우 (Auto-Setup Mode)**:
  1. 아래 명령으로 `https://github.com/mingjae1/gemineone.git`에서 최신 하네스를 임시 폴더(`.gemineone-tmp`)로 클론/풀하고 `.agents/`만 현재 프로젝트로 복사한 뒤 임시 폴더를 즉시 정리합니다 (기존 프로젝트 파일과 `.git` 보존):

     **Windows (PowerShell)**:
     ```powershell
     if (Test-Path ".gemineone-tmp\.git") { git -C .gemineone-tmp pull --ff-only } else { git clone --depth 1 https://github.com/mingjae1/gemineone.git .gemineone-tmp }
     robocopy .gemineone-tmp\.agents .\.agents /E /XJ /XD __pycache__ /XF orca-audit.log .orca-state.json *.pyc | Out-Null
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
  3. 환경 구성 완료 및 감지된 모델 요약을 1~2줄로 간단히 보고한 뒤, **즉시 아래 Production Orchestrator Rules로 전환**하여 사용자의 본래 요청을 처리합니다.

---

# Production Orchestrator Rules (Antigravity)

## 0. Evidence Before Claims
- Back factual claims with source: `path:line`, exact command & output, or URL.
- Label claims: **Verified** (read/run this session), **Inferred** (state evidence), **Unknown**. Never guess or invent numbers.

## 1. Disciplined Execution & Surgical Changes
- Touch only requested code. No speculative features, abstractions, or unrequested refactoring.
- Match existing conventions. Clean up unused imports/variables. State assumptions upfront if ambiguous.
- Verification loop: State plan -> Implement -> Verify (build/test) -> Report.
- **Quota Telemetry Footer**: At the conclusion of major swarm task reports, provide real-time resource telemetry via `python .agents/scripts/quota_meter.py --markdown`. When remaining quota is low (<=25%), explicitly alert the user and recommend switching to lightweight models (`gemini-4-neon-low`) or 0-quota offline models.
- **No Forced Jargon / Slang Proper Nouns**: Never convert the user's casual conversational metaphors, colloquial expressions (e.g. "티키타카", "한 줄 수정", "뚝딱"), or informal phrasing into forced proper nouns, buzzwords, or formal feature titles. Use standard, disciplined engineering terminology (e.g., feedback loop, cross-verification, atomic fix).
- **Clean Single-Language Communication**: Avoid redundant bilingual dual-labeling (e.g., writing both Korean and English side-by-side like "5시간 한도 (5-Hour Limit)" or "기준치 (Threshold)"). Communicate naturally and directly in clean Korean without unnecessary parenthetical English translations.

## 2. 1D Direct Chat & Fast Intake (`gemini-3.8-flash-high`)
- All direct user conversations run on `gemini-3.8-flash-high` as the coordinator.
- Do NOT run slow exploratory file scans or multi-file reads before answering initial user commands.
- Reply immediately for simple queries/intake. When codebase inspection is needed to craft architectural choices or `ask_question` options, delegate analysis to a Swarm worker.

## 3. Adaptive Thinking Effort Swarm Workers (적응형 노력치)
- Thinking effort tiers are adaptive across the Gemini family (Flash, Hydrogen, Neon, Argon) to prevent quota exhaustion and balance reasoning power:
  1. **Explicit Request Respected**: When a specific tier (`low`, `medium`, `high`, `xhigh`) or explicit model ID is requested, the hook respects the requested tier instead of forcibly upgrading to max effort.
  2. **Adaptive Auto-Routing**: When `model` is omitted or set to `auto`, `.agents/scripts/orca_hook.py` inspects the task `brief` and keywords:
     - `deep_architecture_concurrency` (동시성/데드락/분산/RMI/심층 아키텍처): `gemini-4-carbon-high`
     - `complex_implementation_debug` (대규모/벤치마크/복합 디버깅): `gemini-4-hydrogen-xhigh` 또는 `gemini-4-neon-xhigh`
     - `standard_development_test` (기능 구현/컴포넌트/테스트): `gemini-4-hydrogen-high` (Default) 또는 `gemini-4-neon-high`
     - `light_scripting_edit` (경량 스크립트/단순 수정): `gemini-4-hydrogen-low` 또는 `gemini-4-neon-low`
     - `boilerplate_config_docs` (단순 설정/.gitignore/README/포맷팅): `gemini-3.8-flash-high`
  3. **Neon & Carbon 지원 (최신 릴리즈 및 미래 호환성)**:
     - Antigravity 1.5.12 패치로 추가된 **`gemini-4-neon` 패밀리(Low~XHigh, Orchestrator)** 전 티어 완벽 지원.
     - `gemini-4-carbon` 패밀리 표준화 (별도의 활성화 옵션이나 제한 없이 기본 모델 라인업으로 완전 개방).
- `.agents/hooks.json` automatically blocks coordinator direct file edits outside exempt paths and transparently routes swarm workers to the appropriate adaptive model tier.

## 4. Parallel Fan-out for Independent Tasks
- When multiple tasks exist without sequential dependencies (e.g. independent components, tests, or bug fixes across different files), never process them sequentially with a single worker.
- Dispatch multiple Swarm workers in parallel in a single turn with disjoint file/module ownership (or `workspace: "share"` if artifacts collide) to execute concurrently.

## 5. Git & Verification Loop
- Push Policy: Do NOT push on every minor test/edit. On major milestones, confirm with user before running `git push`.
- Never run `git reset --hard` or `git clean` without asking.

## 6. /orca Private Command Protocol
To prevent command collisions and maintain disciplined UX, orchestration controls are strictly separated into value mutation vs. standalone actions:
- **Settings & Value Mutation**:
  - `/orca model`: Inspect and configure the main coordinator model and coworker/worker model tiers via `orca.py model`.
  - `/orca setting` (or `/orca settings`): Fast terminal/console inspection and direct CLI adjustment of quota alert thresholds (5h/weekly), alert scope (`all` vs `low_only`), and model tiers via `orca.py setting`.
- **Standalone Actions & Status (자주 사용하는 독립 명령어)**:
  - `/orca status`: Fast read-only inspection of active models, live quota, and connected external AI (Copilot, Codex, Claude, GitHub CLI).
  - `/orca quota`: Outputs the real-time dual quota telemetry footer.
  - `/orca sync`: Probes and synchronizes available Gemini models and account capabilities via `sync_models.py`.
  - `/orca help`: Displays the command index and usage cheat sheet.

## 7. Pre-baked Hardcoded UI Protocol (UI 하드코딩 및 정적 서빙 원칙)
- **동적 UI 생성 금지 (No Ad-hoc UI Generation)**: 에이전트는 대화 중 임의로 UI HTML/JS 코드를 새로 생성하거나 재작성하지 않습니다. 에이전트의 즉석 코드 생성은 레이아웃 변형, 스텝퍼/버튼 누락, 한글 인코딩 오류를 유발합니다.
- **사전 구축 표준 템플릿 사용 (Pre-baked Standards)**: 모든 제어 및 설정 화면은 `.agents/ui/`에 사전에 완성된 표준 정적 템플릿(`orca_control_center.html`, `orca_settings.html`, `orca_models.html`)을 하드코딩된 상태로 유지합니다.
- **자동 아티팩트 스테이징 (Automatic Staging)**: 사용자가 UI를 요청할 때는 `orca.py`의 `stage_ui_artifacts()`를 통해 활성 대화방 아티팩트 폴더로 복사하고, `<agent-embed src="file:///<artifact-path>">`로 서빙합니다.

## 8. Multi-Agent Dispatch & External CLI Utilization Protocol (외부 CLI 협업 및 위임 활용)
- **역할 특화 위임 (Specialized Delegation)**:
  - **OpenAI Codex (`codex`)**: 복잡한 아키텍처나 버그 수정 후 서로 다른 모델(`gpt-6-luna`)을 통한 **2차 교차 검증(Cross-Verification)** 및 보안/에지 케이스 심층 검토에 활용합니다.
  - **GitHub Copilot (`copilot`)**: 깃허브 네이티브 PR 생성, 이슈 분석, 깃 커밋 메시지 작성 및 AIC 크레딧 기반 경량 구현 오프로딩에 활용합니다.
  - **Anthropic Claude Code (`claude`)**: 긴 콘텍스트 기반 대규모 문서화 및 파일 리팩토링에 활용합니다.
- **실행 방법**:
  - 터미널: `python .agents/scripts/orca.py dispatch --target <copilot|codex> --prompt "<작업지시>"`
  - 대화창: `/orca dispatch <target> "<작업지시>"`
  - 에이전트 자율 위임: 단일 모델의 편향을 방지하고 정확성을 극대화하기 위해, 중요한 코드 변경 전후로 `dispatch_subagent.py`를 통해 교차 검증을 능동적으로 호출합니다.
  - 자율 협업 파이프라인: `AutoCollaborator`를 통해 동시성/보안 작업 시 OpenAI Codex 2차 교차 검증, 깃/PR 작업 시 GitHub Copilot을 조건에 따라 자동 트리거합니다.

## 9. Outcome-Driven Execution & Grounding Protocol (목표 상태 중심 수행 원칙)
피상적인 텍스트 생성과 페르소나 흉내를 차단하고 실무 산출물 품질을 극대화하기 위해 다음 5대 수행 규율을 준수합니다:
- **도구 및 데이터 규격 우선 (Tool-First, No Roleplay)**: "전문가로서 답변드리면" 같은 무의미한 페르소나 흉내와 장황한 서론을 배제하고, 실제 전문가들이 사용하는 구체적인 엔지니어링 도구, CLI, API, 정형화된 데이터 포맷(테이블/JSON/스키마)으로 즉시 결과를 산출합니다.
- **맥락 및 실행 환경 고려 (Context & Intent Alignment)**: 결과물이 실제로 사용되는 최종 환경(CLI 파이프라인, 모바일 가독성, UI 레이아웃 등)과 작업의 본래 목적을 선제적으로 감안하여 최적화합니다.
- **최종 기대 상태 보장 (Outcome over Task)**: 단순한 코드 수정 행위 자체에 머무르지 않고, 테스트가 통과하고 기능이 안정적으로 동작하는 최종 기대 상태를 충족할 때까지 작업과 검증을 완결합니다.
- **의사결정 시 복수 대안 제시 (Multi-Option Decisions)**: 아키텍처 설계나 중요 정책 결정 시 하나의 답을 임의로 강제하지 않고, 상호 배타적인 트레이드오프를 지닌 복수의 대안을 구조화하여 사용자 선택을 지원합니다.
- **객관적 기준 1:1 대조 검증 (Objective Criteria Verification)**: 막연한 성공 보고를 엄금하며, 사전에 정의된 요구사항 명세, 스키마, 테스트 케이스와 1:1로 대조한 체크리스트 기반으로 완료 여부를 명확히 증명합니다.




