# SPEC-15 Decode Evaluation Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the first stable decode-only top-level evaluation pipeline on top of the existing descriptor-driven performance artifacts.

**Architecture:** Reuse the current run-root chain through `run-performance-estimation` and add a thin aggregation layer for decode scenarios only. The new foundation should consume stable perf, coverage, and memory artifacts, emit a decode-facing report focused on token latency and KV access cost, and reject prefill scenarios explicitly instead of silently reusing decode report semantics.

**Tech Stack:** Python 3.14, Pydantic models, existing run-root pipeline/CLI pattern, pytest unit/smoke tests.

---

### Task 1: Add Decode Evaluation Report Contract

**Files:**
- Create: `src/llm_sched/contracts/decode_report.py`
- Modify: `src/llm_sched/contracts/__init__.py`
- Create: `tests/unit/contracts/test_decode_report.py`

**Step 1: Write the failing test**

Add a contract test covering:
- `run_id`
- `graph_id`
- `scenario_name`
- `schedule_kind`
- `token_latency`
- `kv_summary`
- `isa_summary`
- `macro_hotspots`

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/contracts/test_decode_report.py -q`
Expected: FAIL because the contract file does not exist.

**Step 3: Write minimal implementation**

Create:
- `DecodeLatencySummary`
- `DecodeKVSummary`
- `DecodeISASummary`
- `DecodeMacroHotspot`
- `DecodeEvaluationReport`

Keep it summary-only. Do not embed full IR artifacts.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/contracts/test_decode_report.py -q`
Expected: PASS

### Task 2: Add Decode Report Builder

**Files:**
- Create: `src/llm_sched/analysis/decode_report_builder.py`
- Modify: `src/llm_sched/analysis/__init__.py`
- Create: `tests/unit/analysis/test_decode_report_builder.py`

**Step 1: Write the failing tests**

Add builder tests for:
- decode scenarios producing positive token-latency fields
- `SDPA_DECODE` presence being surfaced explicitly
- KV-related cycles and bytes being aggregated into KV summary
- ISA gap counts being surfaced in the top-level report
- prefill scenarios being rejected explicitly

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/analysis/test_decode_report_builder.py -q`
Expected: FAIL because the builder does not exist.

**Step 3: Write minimal implementation**

Implement:
- `build_decode_evaluation_report(run_id, scenario, perf_summary, coverage_report, memory_plan)`

Use only existing artifact contracts. Do not add layer breakdown in this batch.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/analysis/test_decode_report_builder.py -q`
Expected: PASS

### Task 3: Add Run-Root Workflow

**Files:**
- Create: `src/llm_sched/pipeline/decode_evaluation.py`
- Modify: `src/llm_sched/pipeline/__init__.py`
- Create: `tests/unit/pipeline/test_decode_evaluation_workflow.py`

**Step 1: Write the failing test**

Add a workflow test verifying:
- input artifacts are `perf_summary_report`, `isa_coverage_report`, and `memory_plan`
- output is `reports/decode_evaluation_report.json`
- manifest/run-summary updates are stable
- prefill scenarios fail cleanly

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/pipeline/test_decode_evaluation_workflow.py -q`
Expected: FAIL because the workflow does not exist.

**Step 3: Write minimal implementation**

Implement:
- `run_decode_evaluation(run_root)`
- load perf summary + coverage + memory plan + scenario
- reject non-decode scenarios with a clear diagnostic
- emit `decode_evaluation_report.json`
- update `manifest.artifact_index`

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/pipeline/test_decode_evaluation_workflow.py -q`
Expected: PASS

### Task 4: Add CLI And Smoke Gates

**Files:**
- Modify: `src/llm_sched/cli/main.py`
- Create: `tests/smoke/test_cli_run_decode_evaluation.py`
- Create: `tests/smoke/test_phase_d_decode_foundation_matrix.py`

**Step 1: Write the failing tests**

Add smoke tests for:
- `llm-sched run-decode-evaluation --run-root ...`
- Gemma3 `single-core/dual-core x decode` matrix
- `decode_evaluation_report.json` existence
- failure path without traceback for prefill scenarios

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/smoke/test_cli_run_decode_evaluation.py tests/smoke/test_phase_d_decode_foundation_matrix.py -q`
Expected: FAIL because the CLI command does not exist.

**Step 3: Write minimal implementation**

Add CLI wiring and user-facing messages only. Do not add auto-rerun of the full compile pipeline in this batch.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/smoke/test_cli_run_decode_evaluation.py tests/smoke/test_phase_d_decode_foundation_matrix.py -q`
Expected: PASS

### Task 5: Docs, Verification, Commit

**Files:**
- Create: `docs/development/phase-d-decode-foundation-handoff.md`
- Modify: `docs/development/README.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`

**Step 1: Update docs**

Document:
- stable decode evaluation assumptions
- `DecodeEvaluationReport` shape
- CLI/workflow entrypoint
- what `SPEC-16/18` may now assume

**Step 2: Run focused verification**

Run:
- `python -m pytest tests/unit/contracts/test_decode_report.py tests/unit/analysis/test_decode_report_builder.py tests/unit/pipeline/test_decode_evaluation_workflow.py tests/smoke/test_cli_run_decode_evaluation.py tests/smoke/test_phase_d_decode_foundation_matrix.py -q`

Expected: PASS

**Step 3: Run full verification**

Run:
- `python -m pytest -q`
- `git diff --check`

Expected: PASS with no diff errors.

**Step 4: Commit**

```bash
git add src/llm_sched/contracts/decode_report.py src/llm_sched/analysis/decode_report_builder.py src/llm_sched/pipeline/decode_evaluation.py src/llm_sched/cli/main.py docs/development/README.md docs/development/evaluation-compiler-roadmap.md docs/development/phase-d-decode-foundation-handoff.md docs/plans/2026-03-07-spec-15-decode-eval-pipeline.md tests/unit/contracts/test_decode_report.py tests/unit/analysis/test_decode_report_builder.py tests/unit/pipeline/test_decode_evaluation_workflow.py tests/smoke/test_cli_run_decode_evaluation.py tests/smoke/test_phase_d_decode_foundation_matrix.py
git commit -m "feat: add spec 15 decode evaluation foundation"
```
