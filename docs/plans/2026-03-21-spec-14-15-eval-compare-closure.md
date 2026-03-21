# SPEC-14/15 Eval-Compare Closure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Strengthen `SPEC-14/15` so prefill/decode evaluation outputs produce a summary-grade compare verdict that analysts can use directly, instead of needing to reopen raw evaluation artifacts to understand the main decision path.

**Architecture:** Keep this slice centered on the existing `PhaseDCompareReport` consumer chain. Reuse the already-landed prefill/decode toplines, fitted metrics, phase rows, node deltas, layer deltas, and pressure summaries, then add a narrow verdict-style summary surface on top of them. This avoids reopening `SPEC-16` UI interaction by default while still making `SPEC-14/15` compare outputs feel like a complete evaluation loop.

**Tech Stack:** Python 3.11, Pydantic contracts, existing Phase D compare builder/workflow/CLI, pytest unit/workflow/smoke tests.

---

### Task 1: Add failing contract coverage for eval-compare verdict summaries

**Files:**
- Modify: `src/llm_sched/contracts/phase_d_compare_report.py`
- Modify: `tests/unit/contracts/test_phase_d_compare_report.py`

**Step 1: Write the failing tests**

Extend the standalone compare-report contract coverage so both `prefill_compares` and `decode_compares` are expected to expose one explicit verdict-style summary surface. Keep the contract narrow and machine-readable.

Lock fields such as:

```python
assert report.prefill_compares[0].verdict_summary.verdict == "candidate-better"
assert report.prefill_compares[0].verdict_summary.primary_metric == "cycles_per_token"
assert report.prefill_compares[0].verdict_summary.primary_phase == "attention"
assert report.prefill_compares[0].verdict_summary.dominant_layer_id == 0
assert report.decode_compares[0].verdict_summary.primary_metric == "critical_path_cycles_per_token"
assert report.decode_compares[0].verdict_summary.dominant_node_id == "nig.node.kvload.0"
```

Also lock one report-level aggregate section, for example:

```python
assert report.prefill_summary.compare_count == 1
assert report.prefill_summary.candidate_better_count == 1
assert report.decode_summary.compare_count == 1
assert report.decode_summary.mixed_count == 0
```

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/contracts/test_phase_d_compare_report.py -q -x
```

Expected: FAIL because the compare-report contract currently has rich rows but no verdict-summary or report-summary sections.

**Step 3: Write minimal implementation**

Add only the narrow summary models needed for this slice, for example:

- one reusable `PhaseDCompareVerdictSummary`
- one reusable `PhaseDCompareModeSummary`
- `verdict_summary` on `PhaseDPrefillCompareRow`
- `verdict_summary` on `PhaseDDecodeCompareRow`
- top-level `prefill_summary` and `decode_summary` on `PhaseDCompareReport`

Keep the models structural and stable:

- prefer enums / labels over free-form prose
- include the chosen primary metric
- include the chosen primary phase if one is available
- include one dominant node id and/or dominant layer id when available
- do not add UI formatting fields

**Step 4: Run test to verify it passes**

Run the same command again and expect PASS.

### Task 2: Build verdict summaries from existing compare surfaces

**Files:**
- Modify: `src/llm_sched/analysis/phase_d_compare_report_builder.py`
- Modify: `tests/unit/analysis/test_phase_d_compare_report_builder.py`

**Step 1: Write the failing tests**

Extend builder coverage so the report builder must derive verdict summaries from the existing compare rows rather than from new upstream artifacts.

Lock behavior such as:

```python
row = report.prefill_compares[0]
assert row.verdict_summary.preferred_target_profile_name == "riscv_npu_dual_core_v1"
assert row.verdict_summary.primary_metric == "cycles_per_token"
assert row.verdict_summary.primary_metric_delta.delta_value < 0.0
assert row.verdict_summary.primary_phase == "attention"
assert row.verdict_summary.dominant_layer_id == 0

decode_row = report.decode_compares[0]
assert decode_row.verdict_summary.primary_metric == "critical_path_cycles_per_token"
assert decode_row.verdict_summary.primary_phase == "kv_io"
assert decode_row.verdict_summary.dominant_node_id == "nig.node.kvload.0"
```

Add one aggregate assertion:

```python
assert report.prefill_summary.candidate_better_count == len(
    [row for row in report.prefill_compares if row.verdict_summary.verdict == "candidate-better"]
)
```

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/analysis/test_phase_d_compare_report_builder.py -q -x
```

Expected: FAIL because the builder currently forwards rich compare rows but does not compute verdict-level summaries or mode aggregates.

**Step 3: Write minimal implementation**

Implement builder helpers that:

- classify each compare row as `candidate-better`, `baseline-better`, `mixed`, or `neutral`
- choose the primary metric by mode:
  - prefill: prefer `cycles_per_token`, then `critical_path_cycles`, then `tokens_per_cycle`
  - decode: prefer `critical_path_cycles_per_token`, then `cycles_per_token`, then `kv_related_cycle_share`
- select a dominant phase from the strongest absolute phase delta already present on the row
- select a dominant node/layer from the strongest available `node_deltas` / `fitted_layer_deltas`
- build lightweight top-level counts for `prefill_summary` and `decode_summary`

Do not introduce new upstream metrics, new workflows, or visualization-specific recommendation logic in this task.

**Step 4: Run test to verify it passes**

Run the same command again and expect PASS.

### Task 3: Preserve the stronger compare closure through workflow and CLI artifacts

**Files:**
- Modify: `tests/unit/pipeline/test_phase_d_compare_workflow.py`
- Modify: `tests/smoke/test_cli_run_phase_d_compare.py`

**Step 1: Write the failing tests**

Add workflow/CLI assertions that only lock the stable public surface:

```python
assert report.prefill_summary.compare_count >= 0
assert report.prefill_compares[0].verdict_summary.primary_metric in {"cycles_per_token", "critical_path_cycles", "tokens_per_cycle"}
assert report.decode_compares[0].verdict_summary.verdict in {
    "candidate-better",
    "baseline-better",
    "mixed",
    "neutral",
}
```

Mirror the same checks in CLI JSON parsing.

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/pipeline/test_phase_d_compare_workflow.py tests/smoke/test_cli_run_phase_d_compare.py -q -x
```

Expected: FAIL because serialized Phase D compare artifacts do not yet expose the new summary sections.

**Step 3: Write minimal implementation**

No workflow-specific production changes should be needed beyond Task 2 if the report builder and contract changes are complete. If serialization gaps appear, fix them in the narrowest place possible.

**Step 4: Run test to verify it passes**

Run the same command again and expect PASS.

### Task 4: Verify the focused regression surface and record the checkpoint

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `README.md`
- Update: `docs/plans/2026-03-21-spec-14-15-eval-compare-closure.md`

**Step 1: Run focused verification**

Run:

```powershell
python -m pytest tests/unit/contracts/test_phase_d_compare_report.py tests/unit/analysis/test_phase_d_compare_report_builder.py tests/unit/pipeline/test_phase_d_compare_workflow.py tests/smoke/test_cli_run_phase_d_compare.py -q
python -m pytest tests/smoke -m local_smoke -q
python -m pytest tests/smoke -m milestone_matrix -q
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q
```

Expected: PASS.

**Step 2: Update the roadmap checkpoint**

If verification is green, record that:

- `SPEC-14/15` compare outputs now expose summary-grade verdicts directly in `PhaseDCompareReport`
- the next analyst decision can be made from compare artifacts themselves without reopening raw prefill/decode reports for the main path
- further `SPEC-16` work should only consume this stronger eval-compare surface instead of inventing replacement logic in UI layers

## Execution Record (2026-03-21)

- implemented:
  - `PhaseDCompareReport` now has:
    - `PhaseDCompareVerdictSummary`
    - `PhaseDCompareModeSummary`
    - row-level `verdict_summary`
    - top-level `prefill_summary` / `decode_summary`
  - `build_phase_d_compare_report(...)` now derives:
    - mode-level verdict counts
    - preferred target profile
    - primary metric and primary phase
    - dominant layer / node hints from existing layer/node delta surfaces
- fresh focused verification:
  - `python -m pytest tests/unit/contracts/test_phase_d_compare_report.py tests/unit/analysis/test_phase_d_compare_report_builder.py tests/unit/pipeline/test_phase_d_compare_workflow.py tests/smoke/test_cli_run_phase_d_compare.py -q` -> `14 passed`
  - `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q` -> `28 passed`
- broader keep-green rerun status:
  - `python -m pytest tests/smoke -m local_smoke -q` -> `11 passed, 70 deselected`
  - `python -m pytest tests/smoke -m milestone_matrix -q` -> `11 passed, 70 deselected`
- current interpretation:
  - the focused `SPEC-14/15` eval-compare verdict slice is implemented and now freshly revalidated across its direct regression surface plus broader keep-green smoke selections
  - this closes the current verdict-summary slice cleanly, but does not by itself mark all remaining `SPEC-14/15` gaps as done

## Execution Record Update (2026-03-21, decode `kv_len` aggregation)

- implemented:
  - `SweepRunRecord` and `SweepComparison` now preserve structured `kv_len`
  - `PhaseDDecodeCompareRow` now forwards `kv_len`
  - `PhaseDCompareReport` now exposes `decode_kv_len_summaries`
  - decode `kv_len` summaries now aggregate:
    - compare count
    - verdict counts
    - preferred target hint
    - average `critical_path_cycles_per_token` delta
    - average `kv_related_cycle_share` delta
- fresh focused verification:
  - `python -m pytest tests/unit/contracts/test_sweep_report.py tests/unit/contracts/test_phase_d_compare_report.py tests/unit/analysis/test_sweep_report_builder.py tests/unit/analysis/test_phase_d_compare_report_builder.py tests/unit/pipeline/test_phase_d_compare_workflow.py tests/smoke/test_cli_run_phase_d_compare.py -q` -> `26 passed`
- updated interpretation:
  - the eval-compare closure lane now covers both row-level verdicts and structured decode scale aggregation
  - the most concrete remaining `SPEC-15` gap has narrowed to token-latency decomposition rather than missing `kv_len` sweep aggregation

## Execution Record Update (2026-03-21, decode token-latency decomposition)

- implemented:
  - `PhaseDCompareReport` now exposes `decode_latency_decomposition_summary`
  - the summary aggregates decode phase deltas across:
    - `projection`
    - `kv_io`
    - `attention`
    - `sync`
    - `other`
  - the summary now carries:
    - `compare_count`
    - `dominant_phase`
    - ordered phase entries with average cycle delta and average cycle-share delta
- fresh focused verification:
  - `python -m pytest tests/unit/contracts/test_phase_d_compare_report.py tests/unit/analysis/test_phase_d_compare_report_builder.py tests/unit/pipeline/test_phase_d_compare_workflow.py tests/smoke/test_cli_run_phase_d_compare.py -q` -> `15 passed`
  - `python -m pytest tests/unit/contracts/test_sweep_report.py tests/unit/contracts/test_phase_d_compare_report.py tests/unit/analysis/test_sweep_report_builder.py tests/unit/analysis/test_phase_d_compare_report_builder.py tests/unit/pipeline/test_phase_d_compare_workflow.py tests/smoke/test_cli_run_phase_d_compare.py -q` -> `26 passed`
- updated interpretation:
  - the decode side of `SPEC-15` now has direct row verdicts, structured `kv_len` aggregation, and explicit token-latency decomposition inside standalone compare artifacts
  - the next most concrete blocker-facing gap should shift back toward remaining `SPEC-14` / cross-mode compare closure rather than more decode top-level summary expansion

## Execution Record Update (2026-03-21, prefill layer decomposition)

- implemented:
  - `PhaseDCompareReport` now exposes `prefill_layer_decomposition_summary`
  - the summary aggregates prefill layer movement across compares and now carries:
    - `compare_count`
    - `dominant_estimated_layer_id`
    - `dominant_fitted_layer_id`
    - ordered layer entries with average estimated/fitted delta and share movement
- fresh focused verification:
  - `python -m pytest tests/unit/contracts/test_phase_d_compare_report.py tests/unit/analysis/test_phase_d_compare_report_builder.py tests/unit/pipeline/test_phase_d_compare_workflow.py tests/smoke/test_cli_run_phase_d_compare.py -q` -> `16 passed`
  - `python -m pytest tests/unit/contracts/test_sweep_report.py tests/unit/contracts/test_phase_d_compare_report.py tests/unit/analysis/test_sweep_report_builder.py tests/unit/analysis/test_phase_d_compare_report_builder.py tests/unit/pipeline/test_phase_d_compare_workflow.py tests/smoke/test_cli_run_phase_d_compare.py -q` -> `27 passed`
- updated interpretation:
  - the prefill side of `SPEC-14` now has both row-level compare surfaces and summary-grade layer decomposition in standalone compare artifacts
  - the next most concrete gap should shift toward cross-mode compare closure rather than more top-level prefill/decode summary additions

## Execution Record Update (2026-03-21, cross-mode compare closure)

- implemented:
  - `PhaseDCompareReport` now exposes `cross_mode_summaries`
  - each cross-mode summary groups compare rows by shared baseline/candidate/profile-diff context
  - each summary now carries:
    - `prefill_compare_count`
    - `decode_compare_count`
    - `alignment_verdict`
    - `shared_preferred_target_profile_name`
    - per-mode `primary_metric`
    - averaged per-mode `primary_metric_delta`
    - per-mode `primary_phase`
- fresh focused verification:
  - `python -m pytest tests/unit/contracts/test_phase_d_compare_report.py tests/unit/analysis/test_phase_d_compare_report_builder.py tests/unit/pipeline/test_phase_d_compare_workflow.py tests/smoke/test_cli_run_phase_d_compare.py -q` -> `17 passed`
  - `python -m pytest tests/unit/contracts/test_sweep_report.py tests/unit/contracts/test_phase_d_compare_report.py tests/unit/analysis/test_sweep_report_builder.py tests/unit/analysis/test_phase_d_compare_report_builder.py tests/unit/pipeline/test_phase_d_compare_workflow.py tests/smoke/test_cli_run_phase_d_compare.py -q` -> `28 passed`
- updated interpretation:
  - the standalone compare artifact can now answer cross-mode agreement for the same target-profile delta instead of forcing analysts back into separate prefill/decode reports
  - the next most concrete gap should shift from adding more top-level compare summaries toward auditing whether any residual blocker still requires raw artifact reopening
