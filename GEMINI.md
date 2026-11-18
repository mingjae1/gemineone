# GEMINI.md - gemineone Agent Harness

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
- Thinking effort tiers are adaptive across the Gemini family (Flash, Hydrogen, Argon) to prevent quota exhaustion and balance reasoning power:
  1. **Explicit Request Respected**: When a specific tier (`low`, `medium`, `high`, `xhigh`) or explicit model ID is requested, the hook respects the requested tier instead of forcibly upgrading to max effort.
  2. **Adaptive Auto-Routing**: When `model` is omitted or set to `auto`, `.agents/scripts/orca_hook.py` inspects the task `brief` and keywords:
     - `deep_architecture_concurrency` (동시성/데드락/분산/RMI/심층 아키텍처): `gemini-4-argon-high`
     - `complex_implementation_debug` (대규모/벤치마크/복합 디버깅): `gemini-4-hydrogen-xhigh`
     - `standard_development_test` (기능 구현/컴포넌트/테스트): `gemini-4-hydrogen-high` (Default)
     - `light_scripting_edit` (경량 스크립트/단순 수정): `gemini-4-hydrogen-low`
     - `boilerplate_config_docs` (단순 설정/.gitignore/README/포맷팅): `gemini-3.8-flash-high`
- `.agents/hooks.json` automatically blocks coordinator direct file edits outside exempt paths and transparently routes swarm workers to the appropriate adaptive model tier.

## 4. Parallel Fan-out for Independent Tasks
- When multiple tasks exist without sequential dependencies (e.g. independent components, tests, or bug fixes across different files), never process them sequentially with a single worker.
- Dispatch multiple Swarm workers in parallel in a single turn with disjoint file/module ownership (or `workspace: "share"` if artifacts collide) to execute concurrently.

## 5. Git & Verification Loop
- Push Policy: Do NOT push on every minor test/edit. On major milestones, confirm with user before running `git push`.
- Never run `git reset --hard` or `git clean` without asking.
