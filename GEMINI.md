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

## 3. Max-Effort Only Swarm Workers
- Thinking effort tiers are locked to **Max Effort** per model family:
  1. `gemini-4-hydrogen-xhigh` (`hydrogen`, default): Code analysis, `ask_question` options preparation, implementation, build/test loops, bug fixes.
  2. `gemini-4-argon-high` (`argon`): Deep architectural design, complex concurrency/RMI debugging, or stubborn bugs escalated from `hydrogen`.
  3. `gemini-3.8-flash-high` (`flash`): Simple config (`.gitignore`), boilerplate, formatting.
- `.agents/hooks.json` automatically blocks coordinator direct file edits outside exempt paths and upgrades any lower-effort model alias passed to `swarm` to its family's max-effort model.

## 4. Parallel Fan-out for Independent Tasks
- When multiple tasks exist without sequential dependencies (e.g. independent components, tests, or bug fixes across different files), never process them sequentially with a single worker.
- Dispatch multiple Swarm workers in parallel in a single turn with disjoint file/module ownership (or `workspace: "share"` if artifacts collide) to execute concurrently.

## 5. Git & Verification Loop
- Push Policy: Do NOT push on every minor test/edit. On major milestones, confirm with user before running `git push`.
- Never run `git reset --hard` or `git clean` without asking.
