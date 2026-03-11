# Phase D Sweep Foundation Handoff

## 2026-03-07 Checkpoint

- `SPEC-16` now has a stable sweep-and-delta foundation.
- `run-sweep-analysis` is the standalone workflow and CLI entrypoint for cross-target reruns and summary-grade delta reporting.
- Gemma3 `single-core/dual-core x prefill/decode` sweep smoke now produces deterministic `sweep_delta_report.json` artifacts.

## 1. What Is Stable Now

The current `SPEC-16` foundation consumes:
- one `SweepSpec` JSON file
- stable target profile paths
- stable scenario profile paths
- one model path
- existing `SPEC-02 -> SPEC-15` run-root workflows

It produces:
- `runs/<target>__<scenario>/...` child run-roots
- `reports/sweep_delta_report.json`
- completed or failed per-run `manifest.json` and `run-summary.json` artifacts under each child run-root

This foundation intentionally reruns the existing compile/evaluation chain. It does not try to compare partially materialized artifacts from arbitrary external run directories.

## 2. Stable Contract

The current `SweepSpec` now fixes these assumptions:
- `baseline_target_profile` must be included in `target_profiles`
- `target_profiles` must be non-empty
- `scenario_profiles` must be non-empty
- one sweep compares target variants against one designated baseline target

The current `SweepDeltaReport` now carries:
- `sweep_name`
- `baseline_target_profile_name`
- `completed_run_count`
- `failed_run_count`
- `run_records`
- `comparisons`
- `issues`

The current `SweepRunRecord` is summary-grade and intentionally small:
- run identity and run-root path
- target/scenario identity
- `mode`
- `schedule_kind`
- top-level metrics
- macro hotspots
- optional failure message

## 3. Current Comparison Policy

The current builder compares runs per `(scenario_name, mode)` group and only against the designated baseline target. It does not compare candidates against each other.

Current metric policy:
- prefill records expose `estimated_cycles`, `tokens_per_cycle`, `cycles_per_token`, `bytes_per_cycle`, and `max_region_utilization`
- decode records expose `estimated_cycles`, `cycles_per_token`, `kv_related_cycle_share`, `kv_related_bytes`, and `sync_cycles`
- metric deltas are only emitted for keys present on both baseline and candidate records

Current macro policy:
- macro deltas are emitted from top-level hotspot summaries
- macro deltas are sorted by absolute cycle delta
- missing macro entries on one side are treated as `0.0`

Current failure policy:
- failed reruns stay visible as `run_failed` issues
- missing completed baseline runs surface as `missing_baseline` issues instead of crashing the sweep

## 4. Workflow And CLI Entry

Workflow:
- `llm_sched.pipeline.run_sweep_analysis(sweep_spec_path, sweep_root)`

CLI:
- `llm-sched run-sweep-analysis --sweep-spec ... --sweep-root ...`

Run structure:
- child runs are materialized under `runs/`
- the aggregate report is materialized under `reports/sweep_delta_report.json`

The current workflow is deliberately serial and deterministic. It does not do parallel execution, retry orchestration, or cached reuse across child runs.

## 5. What SPEC-18 Can Assume

Visualization-facing work may now assume:
- prefill and decode already have stable top-level evaluation contracts
- sweep outputs already normalize those reports into one cross-run delta artifact
- failed runs and missing baselines are explicit report data, not implicit workflow failures

`SPEC-18` should not need to rediscover:
- how to rerun a target/scenario matrix
- how to locate child run-roots within one sweep workspace
- how baseline-vs-candidate whole-run deltas are encoded

## 6. What Is Still Missing

The current `SPEC-16` foundation still lacks:
- layer-level or block-level diffing
- parallel sweep execution
- cached reuse of prior run-roots
- scenario-to-scenario comparison within one report
- richer multi-baseline or pairwise comparison modes

These are follow-on Phase D and Phase E items, not reasons to reopen the current sweep contract.

## 7. Recommended Next Step

Next work should move into `SPEC-18`:
1. Package `prefill/decode/sweep` reports into a visualization-facing data service or static bundle contract.
2. Keep the current sweep report as the summary-grade source of truth for cross-run deltas.
3. Defer deeper comparison granularity to later `SPEC-16` hardening once UI consumers prove they need it.
