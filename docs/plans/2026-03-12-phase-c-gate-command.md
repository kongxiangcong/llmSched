# Phase C Gate Command Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a formal `run-phase-c-gate` CLI command that regenerates the canonical Phase C matrix report and exits nonzero unless the matrix is ready for acceptance.

**Architecture:** Reuse the existing `run-phase-c-acceptance` workflow and report contract rather than introducing a separate gate pipeline. Centralize matrix-summary formatting in the CLI, then layer one extra readiness check on top so the same report path serves both inspection and gating.

**Tech Stack:** Python, Typer CLI, existing Phase C pipeline/report contracts, pytest smoke tests, Markdown docs

---

### Task 1: Add failing smoke coverage

**Files:**
- Modify: `D:\workspace\llmSched\tests\smoke\test_cli_help.py`
- Create: `D:\workspace\llmSched\tests\smoke\test_cli_run_phase_c_gate.py`

**Step 1: Cover discovery**

Assert `--help` lists `run-phase-c-gate`.

**Step 2: Cover ready matrix pass**

Build the canonical four-case smoke workspace and assert:
- exit code `0`
- `Matrix summary: status=ready_for_acceptance`
- `Phase C gate: PASS`

**Step 3: Cover incomplete matrix block**

Build a three-case workspace and assert:
- exit code `1`
- `Matrix summary: status=in_progress`
- `missing=1`
- `Phase C gate: BLOCKED`

### Task 2: Implement the CLI gate

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\cli\main.py`

**Step 1: Factor shared acceptance/report loading**

Move `run-phase-c-acceptance` summary printing into a small helper that:
- executes the workflow
- handles workflow/report generation failures
- loads `PhaseCAcceptanceReport`
- prints the matrix summary

**Step 2: Add `run-phase-c-gate`**

Call the shared helper and fail with exit code `1` unless `report.status == "ready_for_acceptance"`.

### Task 3: Refresh docs and verify

**Files:**
- Modify: `D:\workspace\llmSched\README.md`
- Modify: `D:\workspace\llmSched\docs\development\phase-c-memory-planner-handoff.md`
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`

**Step 1: Document the formal gate**

Record that `run-phase-c-gate` is now the official `M2 / SPEC-08` entrypoint and that it exits nonzero on an incomplete matrix.

**Step 2: Verify**

```powershell
python -m pytest tests/smoke/test_cli_help.py tests/smoke/test_cli_run_phase_c_gate.py tests/smoke/test_phase_c_acceptance_matrix.py tests/smoke/test_cli_run_phase_c_acceptance.py -q
```

Expected: pass
