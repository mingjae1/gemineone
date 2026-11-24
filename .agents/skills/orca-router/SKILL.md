---
name: orca-router
description: >-
  Project multi-model orchestrator skill enforcing 1D Flash fast intake,
  adaptive thinking effort swarm workers across Gemini family (Flash, Hydrogen, Neon, Argon),
  and parallel fan-out via .agents/hooks.json.
---

# ORCA Multi-Model Router Skill

This project enforces worker delegation via `.agents/hooks.json` (`.agents/scripts/orca_hook.py`) and `.agents/orca-config.json`.
Direct file edits (`edit_file`, `write_file`, etc.) by the main coordinator outside exempt paths (`.agents/`, `.gemini/`, `brain`, `GEMINI.md`) are blocked (`"decision": "deny"`).

## 1. 1D Direct Chat & Fast Intake (`gemini-3.8-flash-high`)
- The user interacts directly **only** with `gemini-3.8-flash-high` as the coordinator.
- On initial user commands, do **NOT** perform slow exploratory file scans or multi-file reads before answering.
- Answer simple questions or obvious clarifications immediately.
- When codebase inspection is needed to craft architectural choices or `ask_question` options, immediately delegate that analysis to a Swarm worker instead of reading the codebase inline.

## 2. Adaptive Thinking Effort Swarm Workers (적응형 노력치)
Thinking effort tiers are adaptive across the Gemini model family to optimize quota consumption and reasoning power:

1. **Explicit Tier Respected**:
   - Explicitly requested tiers (`low`, `medium`, `high`, `xhigh`) or specific models (e.g. `gemini-4-hydrogen-low`, `gemini-3.8-flash-medium`) are honored directly without forced upgrading.
2. **Adaptive Auto-Routing (Brief & Keyword Analysis)**:
   - When `model` is omitted or set to `auto`, `orca_hook.py` evaluates the task brief and keywords:
     - **Deep Architecture / Concurrency (`gemini-4-argon-high`, Carbon 활성화 시 `gemini-4-carbon-high`)**: Distributed systems, RMI, concurrency, race conditions, deadlocks, memory leaks.
     - **Complex Implementation / Debug (`gemini-4-hydrogen-xhigh`)**: Large-scale multi-module changes, heavy benchmarks, comprehensive test suites.
     - **Standard Development & Tests (`gemini-4-hydrogen-high`, Default)**: Standard feature implementation, component authoring, unit test loops, and bug fixes.
     - **Light Scripting & Minor Edits (`gemini-4-hydrogen-low`)**: Minor refactoring, script tweaks, simple rename.
     - **Boilerplate / Config / Docs (`gemini-3.8-flash-high`)**: `.gitignore`, formatting, typos, README updates, trivial config.
3. **Carbon Forward-Compatibility (미래 호환성)**:
   - `gemini-4-carbon` 패밀리(`low`~`xhigh`) 사전 등록.
   - `enableCarbon: false` 시 Carbon 요청은 `carbonFallback`(`gemini-4-argon-high`)으로 부드럽게 대체(Graceful Fallback)되어 권한 미보유 환경에서의 에러를 방지합니다.
   - Carbon이 열려 있는 환경에서는 `enableCarbon: true`로 즉시 풀파워를 발휘합니다.

## 3. Parallel Fan-out for Independent Tasks
When multiple tasks exist without sequential dependencies:
- **Never execute sequentially with a single worker.**
- **Dispatch in parallel**: In a single coordinator turn, spawn multiple workers concurrently (e.g. `add` for `course-dev` and `student-dev`, or pass `tasks` / `n` for sharded pools).
- **Enforce Disjoint Ownership**: Explicitly specify the files/components each worker owns in its `brief` (e.g. Worker A owns `Components/Course/`, Worker B owns `Components/Student/`). When build artifacts might collide, use `workspace: "share"`.
- **Scatter-Gather Coordination**: Workers run concurrently and post `@coordinator [done] <summary>` when finished. The coordinator waits (`swarm_wait`), gathers all `[done]` posts, and performs an integrated build/test check.

## 4. Verification Protocol
1. After calling `swarm{action: "add", ...}`, call `swarm{action: "status"}` and display the returned `model` field and the `open_board` link on its own line.
2. Check `.agents/orca-audit.log` to verify the exact `conversationId`, `callerModelName`, and `resolvedModel` recorded by the hook.

## 5. Disciplined Communication
- Never convert the user's casual conversational metaphors, colloquial expressions (e.g. "티키타카", "한 줄 수정", "뚝딱"), or informal phrasing into forced proper nouns, buzzwords, or formal feature titles.
- Use standard, disciplined engineering terminology (e.g., feedback loop, cross-verification, atomic fix).
