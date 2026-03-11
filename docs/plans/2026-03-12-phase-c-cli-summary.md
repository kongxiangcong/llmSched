# Phase C CLI Summary Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make `run-phase-c-acceptance` print a one-line matrix summary so the Phase C gate is visible from CLI output without reopening JSON artifacts.

**Architecture:** Keep the acceptance workflow unchanged. After a successful run, have the CLI read the emitted `phase_c_acceptance_report.json` and print a concise summary line with overall status and matrix counts. Reuse the report contract rather than re-deriving counts in CLI.

**Tech Stack:** Python, Typer CLI, existing Phase C report contract, pytest smoke tests, Markdown docs

---

### Task 1: Add failing CLI-output tests

**Files:**
- Modify: `D:\workspace\llmSched\tests\smoke\test_phase_c_acceptance_matrix.py`
- Modify: `D:\workspace\llmSched\tests\smoke\test_cli_run_phase_c_acceptance.py`

**Step 1: Success-path red test**

Assert CLI stdout includes a line like:
- `Matrix summary: status=ready_for_acceptance`
- `planner_blocked=0`
- `downstream_blocked=0`

**Step 2: Explicit-run-roots red test**

Assert the explicit `--run-root` path also prints the same summary line.

### Task 2: Implement the CLI summary

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\cli\main.py`

**Step 1: Read the emitted report**

After `run_phase_c_acceptance` succeeds, load `result.report_path` as `PhaseCAcceptanceReport`.

**Step 2: Print one-line summary**

Print:
- overall status
- ready count
- blocked count
- planner_blocked count
- downstream_blocked count
- missing count
- duplicate count

### Task 3: Refresh docs and verify

**Files:**
- Modify: `D:\workspace\llmSched\docs\development\phase-c-memory-planner-handoff.md`

**Step 1: Document the CLI visibility**

Record that the matrix gate is now visible directly in CLI output.

**Step 2: Verify**

```powershell
python -m pytest tests/smoke/test_phase_c_acceptance_matrix.py tests/smoke/test_cli_run_phase_c_acceptance.py -q
```

Expected: pass
