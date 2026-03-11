# Phase C Acceptance Smoke/CLI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add cached smoke coverage for `run-phase-c-acceptance` so the canonical `single-core/dual-core x prefill/decode` matrix is exercised through the real CLI.

**Architecture:** Reuse the existing smoke cache that already prepares run roots up to `visualization_bundle`. Add one matrix-style smoke test that builds a four-run workspace and asserts `phase_c_acceptance_report.json` is `ready_for_acceptance`, then add one dedicated CLI smoke test that exercises the command surface and error handling without reopening planner semantics or adding new pipeline stages.

**Tech Stack:** Python, pytest smoke suite, cached CLI run roots, Typer CLI, JSON artifact assertions

---

### Task 1: Add failing smoke/CLI tests

**Files:**
- Create: `D:\workspace\llmSched\tests\smoke\test_phase_c_acceptance_matrix.py`
- Create: `D:\workspace\llmSched\tests\smoke\test_cli_run_phase_c_acceptance.py`

**Step 1: Write the matrix smoke test**

Build a workspace with four cached run roots:
- `single-core + prefill`
- `single-core + decode`
- `dual-core + prefill`
- `dual-core + decode`

Use `prepared_smoke_run_root_factory(..., final_stage="visualization_bundle")`, then invoke `run-phase-c-acceptance` against that workspace and assert:
- command succeeds
- `reports/phase_c_acceptance_report.json` exists
- `status == "ready_for_acceptance"`
- all four canonical case ids are present
- each run now has `reports/memory_planner_closure_report.json`

**Step 2: Write the dedicated CLI smoke test**

Exercise the command surface more directly:
- use explicit `--run-root` arguments for the same four cached runs
- assert success text appears in stdout
- assert no traceback is printed

Also add one failure-path assertion:
- point `--workspace-root` at an empty directory
- assert exit code `1`
- assert stdout contains `Phase C acceptance: ERROR`
- assert stderr has no traceback

**Step 3: Run the red slice**

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/smoke/test_phase_c_acceptance_matrix.py tests/smoke/test_cli_run_phase_c_acceptance.py -q
```

Expected: fail because the smoke tests and any remaining CLI gaps are not implemented yet.

### Task 2: Implement the minimal smoke/CLI support

**Files:**
- Modify: `D:\workspace\llmSched\tests\smoke\conftest.py` (only if cache staging needs a new reusable helper)
- Modify: `D:\workspace\llmSched\src\llm_sched\pipeline\phase_c_acceptance.py` (only if smoke exposes a real CLI/workspace discovery gap)
- Modify: `D:\workspace\llmSched\src\llm_sched\cli\main.py` (only if smoke exposes a user-facing command gap)

**Step 1: Keep the smoke path cache-backed**

Prefer reusing the existing `visualization_bundle` prepared stage so the smoke tests only exercise:
- workspace/run-root discovery
- closure regeneration
- acceptance aggregation

Do not add a heavier cached stage unless the tests prove it is necessary.

**Step 2: Fix only real gaps exposed by the red tests**

Possible minimal fixes:
- shared helper for building the canonical four-run workspace in smoke tests
- CLI stdout/error message polish
- workspace discovery edge-case handling

Do not reopen acceptance semantics or planner contracts.

**Step 3: Re-run the focused slice**

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/smoke/test_phase_c_acceptance_matrix.py tests/smoke/test_cli_run_phase_c_acceptance.py -q
```

Expected: pass

### Task 3: Refresh docs and verify the closure slice

**Files:**
- Modify: `D:\workspace\llmSched\README.md`
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`

**Step 1: Document the new smoke gate**

Record that:
- Phase C acceptance now has a cached CLI smoke path
- the canonical matrix can be regenerated from smoke infrastructure, not only unit workflow tests

**Step 2: Run the verification slice**

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/smoke/test_phase_c_acceptance_matrix.py tests/smoke/test_cli_run_phase_c_acceptance.py tests/unit/contracts/test_phase_c_acceptance_report.py tests/unit/analysis/test_phase_c_acceptance_report_builder.py tests/unit/pipeline/test_phase_c_acceptance_workflow.py tests/unit/contracts/test_memory_planner_closure_report.py tests/unit/analysis/test_memory_planner_closure_builder.py tests/unit/pipeline/test_memory_planner_closure_workflow.py -q
```

Expected: pass
