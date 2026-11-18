---
name: orca-router
description: >-
  Project multi-model orchestrator skill enforcing 1D Flash fast intake,
  max-effort swarm workers (gemini-3.8-flash-high, gemini-4-hydrogen-xhigh,
  gemini-4-argon-high), and parallel fan-out via .agents/hooks.json.
---

# ORCA Multi-Model Router Skill

This project enforces worker delegation via `.agents/hooks.json` (`.agents/scripts/orca_hook.py`) and `.agents/orca-config.json`.
Direct file edits (`edit_file`, `write_file`, etc.) by the main coordinator outside exempt paths (`.agents/`, `.gemini/`, `brain`, `GEMINI.md`) are blocked (`"decision": "deny"`).

## 1. 1D Direct Chat & Fast Intake (`gemini-3.8-flash-high`)
- The user interacts directly **only** with `gemini-3.8-flash-high` as the coordinator.
- On initial user commands, do **NOT** perform slow exploratory file scans or multi-file reads before answering.
- Answer simple questions or obvious clarifications immediately.
- When codebase inspection is needed to craft architectural choices or `ask_question` options, immediately delegate that analysis to a Swarm worker instead of reading the codebase inline.

## 2. Max-Effort Only Swarm Workers
Thinking effort tiers are locked to **Max Effort** per model family. Any lower-effort model ID or alias passed to `swarm` is automatically upgraded by `orca_hook.py` to its family's max-effort model:

1. **Routine / Config / Boilerplate (`gemini-3.8-flash-high`, alias: `flash`)**
   - `.gitignore` setup, simple file generation, formatting, or trivial edits.
2. **Default Analysis, Implementation & Test Loops (`gemini-4-hydrogen-xhigh`, alias: `hydrogen`)**
   - Codebase inspection to prepare structured `ask_question` options (pass `fork: "coordinator"` when prior conversation context is needed).
   - Multi-step implementation, Gradle/javac builds, test runs, and bug fixes.
3. **Deep Architecture / Complex Escalation (`gemini-4-argon-high`, alias: `argon`)**
   - Deep architectural design, complex concurrency/RMI debugging, or stubborn bugs escalated from `hydrogen`.

## 3. Parallel Fan-out for Independent Tasks
When multiple tasks exist without sequential dependencies:
- **Never execute sequentially with a single worker.**
- **Dispatch in parallel**: In a single coordinator turn, spawn multiple workers concurrently (e.g. `add` for `course-dev` and `student-dev`, or pass `tasks` / `n` for sharded pools).
- **Enforce Disjoint Ownership**: Explicitly specify the files/components each worker owns in its `brief` (e.g. Worker A owns `Components/Course/`, Worker B owns `Components/Student/`). When build artifacts might collide, use `workspace: "share"`.
- **Scatter-Gather Coordination**: Workers run concurrently and post `@coordinator [done] <summary>` when finished. The coordinator waits (`swarm_wait`), gathers all `[done]` posts, and performs an integrated build/test check.

## 4. Verification Protocol
1. After calling `swarm{action: "add", ...}`, call `swarm{action: "status"}` and display the returned `model` field and the `open_board` link on its own line.
2. Check `.agents/orca-audit.log` to verify the exact `conversationId`, `callerModelName`, and `resolvedModel` recorded by the hook.
