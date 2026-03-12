# SPEC-13 Token-Phase Attribution Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Promote decode/prefill phase-level cycle and byte attribution into the stable `PerfSummaryReport` contract, then make `SPEC-14/15` consume that surface directly instead of reconstructing top-level phase summaries from raw macro buckets.

**Architecture:** Keep this slice narrow. Reuse the current descriptor-estimator macro classification as the first stable attribution model, but move the aggregation into `build_perf_summary_report(...)` so the phase summary becomes part of the canonical SPEC-13 output. Update decode and prefill report builders to consume the structured perf phase attribution directly, while leaving deeper cycle-model changes and richer diff modes for later slices.

**Tech Stack:** Python 3.11, Pydantic contracts, existing SPEC-13/14/15 analysis builders, pytest unit and workflow tests.

## Execution Policy

The user already approved immediate implementation, so this plan is executed in the current session without pausing for an execution-mode choice.

## Execution Result (2026-03-12)

Completed as planned.

Verification:
- `python -m pytest tests/unit/contracts/test_perf_report.py tests/unit/analysis/test_perf_summary_builder.py tests/unit/analysis/test_decode_report_builder.py tests/unit/analysis/test_prefill_report_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py -q`
  - `15 passed in 0.50s`
- `python -m pytest tests/smoke/test_cli_run_performance_estimation.py -q`
  - `2 passed in 111.92s`

---

### Task 1: Add Failing Contract Coverage For Stable Perf Phase Attribution

**Files:**
- Modify: `src/llm_sched/contracts/perf_report.py`
- Modify: `tests/unit/contracts/test_perf_report.py`

**Step 1: Write the failing tests**

Assert that:
- `PerfSummaryReport` exposes one stable `phase_attribution` surface
- the surface carries cycles and bytes for named top-level phases instead of only raw per-macro totals
- decode-oriented phases cover at least `projection`, `kv_io`, `attention`, `sync`, and `other`
- prefill-oriented consumers can also rely on the same structured surface without re-reading raw macro buckets

**Step 2: Run test to verify it fails**

Run:
```powershell
python -m pytest tests/unit/contracts/test_perf_report.py -q
```

Expected: FAIL because `PerfSummaryReport` does not yet define a stable phase-attribution field.

**Step 3: Write minimal implementation**

Implement:
- one small Pydantic model for a perf phase summary row
- one `phase_attribution` mapping on `PerfSummaryReport`
- compatibility-safe retention of existing `per_macro_*`, `per_node_*`, and `per_layer_*` fields

**Step 4: Run test to verify it passes**

Run the same command again and expect PASS.

### Task 2: Add Failing SPEC-13 Builder Tests For Phase Aggregation

**Files:**
- Modify: `src/llm_sched/analysis/descriptor_estimator.py`
- Modify: `tests/unit/analysis/test_perf_summary_builder.py`
- Modify: `tests/unit/pipeline/test_performance_estimation_workflow.py`

**Step 1: Write the failing tests**

Assert that:
- `build_perf_summary_report(...)` populates `phase_attribution` from descriptor-backed records
- projection, KV IO, attention, sync, and residual-other totals are aggregated deterministically
- the workflow artifact written by `run_performance_estimation(...)` preserves the new field end to end

**Step 2: Run test to verify it fails**

Run:
```powershell
python -m pytest `
  tests/unit/analysis/test_perf_summary_builder.py `
  tests/unit/pipeline/test_performance_estimation_workflow.py -q
```

Expected: FAIL because the builder currently only emits raw macro/node/layer totals.

**Step 3: Write minimal implementation**

Implement:
- one shared SPEC-13 phase-classification helper in `descriptor_estimator.py`
- aggregation of phase cycles and bytes inside `build_perf_summary_report(...)`
- deterministic handling of `sync` and `other` so totals remain internally consistent

Do not attempt a deeper tile- or memory-plan-aware estimator in this batch.

**Step 4: Run test to verify it passes**

Run the same command again and expect PASS.

### Task 3: Add Failing SPEC-14/15 Consumer Tests For Direct Perf Phase Consumption

**Files:**
- Modify: `src/llm_sched/analysis/decode_report_builder.py`
- Modify: `src/llm_sched/analysis/prefill_report_builder.py`
- Modify: `tests/unit/analysis/test_decode_report_builder.py`
- Modify: `tests/unit/analysis/test_prefill_report_builder.py`

**Step 1: Write the failing tests**

Assert that:
- decode report latency fields are sourced from `perf_summary.phase_attribution`
- decode no longer needs to reconstruct `projection/kv_io/attention` from raw `per_macro_cycles`
- prefill can derive its dominant-compute judgment from the same structured perf phase surface
- existing macro/node/layer hotspot outputs remain unchanged

**Step 2: Run test to verify it fails**

Run:
```powershell
python -m pytest `
  tests/unit/analysis/test_decode_report_builder.py `
  tests/unit/analysis/test_prefill_report_builder.py -q
```

Expected: FAIL because the builders still consume raw macro buckets for top-level phase summaries.

**Step 3: Write minimal implementation**

Implement:
- decode top-level latency reading `projection`, `kv_io`, `attention`, `sync`, and `other` directly from `phase_attribution`
- prefill MXU-dominance reading a shared compute-heavy phase from the same surface, while keeping current throughput and memory summary logic
- conservative fallback to existing macro totals only if `phase_attribution` is absent in hand-built fixtures outside the workflow

**Step 4: Run test to verify it passes**

Run the same command again and expect PASS.

### Task 4: Verify And Record The SPEC-13 Closure Slice

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/plans/2026-03-12-spec-13-token-phase-attribution.md`

**Step 1: Run focused verification**

Run:
```powershell
python -m pytest `
  tests/unit/contracts/test_perf_report.py `
  tests/unit/analysis/test_perf_summary_builder.py `
  tests/unit/analysis/test_decode_report_builder.py `
  tests/unit/analysis/test_prefill_report_builder.py `
  tests/unit/pipeline/test_performance_estimation_workflow.py -q
```

Expected: PASS.

**Step 2: Update roadmap with one narrow checkpoint**

If verification is green, add one `SPEC-13` checkpoint documenting that phase-level top summary attribution is now a stable perf contract consumed by `SPEC-14/15`, while deeper cycle modeling and richer diff views remain open follow-up work.
