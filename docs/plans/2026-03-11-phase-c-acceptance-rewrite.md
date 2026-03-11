# Phase C Acceptance Rewrite Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rewrite the remaining `SPEC-08~12` Phase C status language from broad backlog phrasing into a narrow acceptance list that matches the current M2 decisions and evidence.

**Architecture:** Keep product code unchanged and update only docs. Normalize the top-level roadmap, milestone summary, and Phase C handoff docs so they all reflect the same post-audit state: `SPEC-09` has an accepted M2 scope boundary, `SPEC-10/11` have completed the remaining helper-store audit batch, `SPEC-12` has a frozen M2 stop-line, and `SPEC-08` is now a planner-closure item rather than a missing-foundation item.

**Tech Stack:** Markdown docs, roadmap/status matrices, Phase C handoff notes

---

### Task 1: Rewrite top-level Phase C status summaries

**Files:**
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\README.md`

**Step 1: Replace broad Phase C gap language**

Update the top status matrix, M2 milestone summary, and P0 list so they describe:
- `SPEC-08` as planner closure plus downstream reuse
- `SPEC-09` as accepted current-scope tiling
- `SPEC-10/11` as acceptance-list closure after the completed helper-store audit batch
- `SPEC-12` as a frozen summary-grade stop-line

**Step 2: Keep the wording consistent with the already-recorded 2026-03-11 checkpoint evidence**

### Task 2: Rewrite Phase C handoff “still missing / next step” sections

**Files:**
- Modify: `D:\workspace\llmSched\docs\development\phase-c-memory-planner-handoff.md`
- Modify: `D:\workspace\llmSched\docs\development\phase-c-tile-planner-handoff.md`
- Modify: `D:\workspace\llmSched\docs\development\phase-c-single-core-scheduler-handoff.md`
- Modify: `D:\workspace\llmSched\docs\development\phase-c-dual-core-scheduler-handoff.md`
- Modify: `D:\workspace\llmSched\docs\development\phase-c-descriptor-handoff.md`

**Step 1: Narrow each remaining-gap section**

Make each file describe only the real accepted closure boundary that remains.

**Step 2: Rewrite each “Recommended Next Step” section**

Use explicit acceptance language instead of generic “expand more coverage” wording.

### Task 3: Verify the rewrite is coherent

**Step 1: Search for stale broad-gap phrases**

Run searches for phrases like:
- `broader macro coverage`
- `richer tile candidate search`
- `descriptor-facing closure`
- `per-record drilldown`

Confirm any remaining hits are either historical checkpoint records or still-correct future work.

**Step 2: Run `git diff --check`**

Confirm the rewrite introduced no whitespace errors.

## Outcome

- Implemented:
  - rewrote the top-level roadmap status matrix, `M2` milestone summary, and current-direction notes
  - rewrote the Phase C handoff `What Is Still Missing` / `Recommended Next Step` sections for `SPEC-08~12`
  - added one explicit roadmap checkpoint recording that the acceptance rewrite is now done
- Verification evidence:
  - targeted stale-phrase search now leaves only intentional current wording plus historical checkpoint records
  - `git diff --check` exits cleanly apart from the existing CRLF warnings already present in this worktree
- Result:
  - `Phase C / M2` docs now read as a narrow acceptance problem instead of a vague unfinished phase
  - the roadmap, README, and handoff docs now point at the same closure boundary
