# 2026-03-21 SPEC-14/15 Residual Blocker Audit

## Goal

Decide whether the current `SPEC-14/15` eval-compare closure lane is already strong enough for the main analyst decision path, or whether one more compare-grade follow-on is still required before this sub-lane can be treated as practically closed.

## Audit Question

Can analysts answer the main compare-loop questions directly from standalone `PhaseDCompareReport` artifacts without reopening raw prefill/decode evaluation artifacts?

## Evidence Reviewed

- compare-artifact surfaces now present in `PhaseDCompareReport`
  - row-level `verdict_summary`
  - top-level `prefill_summary` / `decode_summary`
  - `decode_kv_len_summaries`
  - `decode_latency_decomposition_summary`
  - `prefill_layer_decomposition_summary`
  - `cross_mode_summaries`
- workflow and smoke evidence already asserting those surfaces:
  - `tests/unit/contracts/test_phase_d_compare_report.py`
  - `tests/unit/analysis/test_phase_d_compare_report_builder.py`
  - `tests/unit/pipeline/test_phase_d_compare_workflow.py`
  - `tests/smoke/test_cli_run_phase_d_compare.py`

## Analyst Closure Checklist

- can the artifact answer which target is preferred for a given compare row?
  - `pass`
- can the artifact answer how decode preference changes across `kv_len` scale?
  - `pass`
- can the artifact answer which decode token-latency phase is driving the change?
  - `pass`
- can the artifact answer which prefill layer movement is dominant across the current compare set?
  - `pass`
- can the artifact answer whether prefill and decode agree on the same target-profile delta?
  - `pass`

## Decision

Decision: `close-enough`

- the main `SPEC-14/15` eval-compare closure question is now answered from the standalone compare artifact itself
- the default analyst path no longer requires reopening raw prefill/decode reports just to decide:
  - who is better
  - how decode behavior changes with `kv_len`
  - which decode phase dominates
  - which prefill layer dominates
  - whether prefill/decode agree for the same candidate target

## What Still Does Not Count As A Reopened Blocker

- scenario-specific anomaly root-cause work that wants every raw layer/node row
- visualization/workspace convenience improvements that only re-present the same compare payload
- more top-level compare summaries that restate questions already answered by the current artifact

## Residual Gaps That Still Exist, But Belong Elsewhere

- `SPEC-13`
  - deeper cycle fitting remains the main remaining blocker-grade uncertainty
  - stronger compare-grade estimator aggregation above current summary surfaces remains open
- `SPEC-16`
  - deeper compare/workspace drill-down is still useful, but should stay a consumer of the current compare artifact rather than a replacement for it
  - parallel execution and cache reuse remain workflow-scale hardening, not missing eval-compare semantics

## Recommended Next Lane

- shift the dominant remaining `M3` blocker lane back to `SPEC-13` deeper cycle fitting plus compare-grade estimator aggregation
- keep any follow-on `SPEC-16` work narrowly attached to consuming this already-closed `SPEC-14/15` compare surface
- do not reopen the current `SPEC-14/15` compare-closure lane unless a new concrete analyst question appears that still cannot be answered from `PhaseDCompareReport`

## Follow-Up Note

- a first `SPEC-13` focused close-out slice is now in progress via `docs/plans/2026-03-21-spec-13-fit-gap-summary.md`
- that slice adds summary-grade estimator trust through `PerfSummaryReport.fit_gap_summary`, while still leaving deeper cycle fitting and broader compare-grade estimator aggregation as the next remaining blocker candidates
