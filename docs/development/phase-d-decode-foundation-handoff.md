# Phase D Decode Foundation Handoff

## 2026-03-09 Memory Hotspot Summary Checkpoint

- New plan: `../plans/2026-03-09-spec-14-15-memory-hotspot-summary.md`
- `SPEC-15` now exposes a first-order memory-hotspot view on top of the already-landed token-latency and KV-summary fields.
- New closure evidence:
  - `DecodeEvaluationReport` now carries `memory_hotspot`
  - `memory_hotspot` now exposes `dominant_address_space`
  - `memory_hotspot` now exposes copied read/write bytes by address space
  - `memory_hotspot` now exposes the hottest VMEM region and its peak utilization
  - decode workflow and Phase D decode smoke remain green with the stronger report contract
- This batch deliberately does not introduce:
  - layer-level hotspot views
  - per-token traffic replay
  - cross-run compare logic

## 2026-03-07 Checkpoint

- `SPEC-15` now has a stable decode-only top-level evaluation foundation.
- `run-decode-evaluation` is the standalone run-root workflow and CLI command for decode-facing reports.
- Gemma3 `single-core/dual-core x decode` smoke now produces deterministic decode evaluation artifacts.

## 1. What Is Stable Now

The current `SPEC-15` foundation consumes:
- `reports/perf_summary_report.json`
- `reports/isa_coverage_report.json`
- `artifacts/memory_plan.json`
- scenario profile

It produces:
- `reports/decode_evaluation_report.json`
- `manifest.artifact_index["decode_evaluation_report"]`
- completed or failed `run-summary.json` updates through the decode-evaluation workflow

This foundation is intentionally summary-grade. It aggregates stable Phase C and `SPEC-13` artifacts and does not rerun the compile chain.

## 2. Stable Contract

The current `DecodeEvaluationReport` now carries:
- `run_id`
- `graph_id`
- `scenario_name`
- `schedule_kind`
- `batch`
- `kv_len`
- `sdpa_decode_present`
- `token_latency`
- `kv_summary`
- `memory_hotspot`
- `isa_summary`
- `macro_hotspots`

Current top-level guarantees:
- only `scenario.mode = decode` is accepted
- token latency is derived from run-level cycles and token count
- KV summary is derived from stable perf totals plus existing KV/memory diagnostics
- ISA gaps stay explicit at the top-level report

## 3. Current Aggregation Policy

The decode evaluator currently models:
- token latency as `estimated_cycles`, `cycles_per_token`, and coarse buckets for projection, KV IO, attention, sync, and other work
- KV summary using `kv_len`, KV formula count, unresolved address count, KV-related cycle share, and KV-related bytes
- memory hotspots using address-space movement totals from `PerfSummaryReport` plus hottest-region data from `MemoryPlanArtifact`
- ISA summary using unmapped block count plus `gap_counts`
- hotspots using sorted per-macro cycle totals from `PerfSummaryReport`

Current `sdpa_decode_present` policy is intentionally simple:
- mark true when `SDPA_DECODE` is present in per-macro cycle totals
- keep it explicit so downstream reports do not need to rediscover decode-path selection

## 4. What SPEC-16 And SPEC-18 Can Assume

Sweep and visualization work may now assume:
- both prefill and decode top-level report formats exist alongside lower-level perf artifacts
- Phase D can expose summary-grade reports without reopening descriptor or scheduler semantics
- single-core and dual-core decode runs are already normalized to one report contract

`SPEC-16/18` should not need to rediscover:
- how token latency is aggregated into a user-facing top-level report
- how KV-related pressure surfaces in evaluation outputs
- how decode-path selection is reflected in stable report fields

## 5. What Is Still Missing

The current `SPEC-15` foundation still lacks:
- finer token-latency decomposition below current macro buckets
- longitudinal `kv_len` sweep views inside one report
- layer-level or token-phase hotspot attribution
- integration with sweep delta reports and visualization-facing data services

These are follow-on Phase D and Phase E items, not reasons to reopen the current perf or scheduler contracts.

## 6. Recommended Next Step

Next work should keep moving forward inside Phase D and E:
1. Start `SPEC-16` using the now-stable prefill/decode top-level reports as sweep inputs.
2. After sweep contracts stabilize, begin `SPEC-18` visualization-facing data packaging.
3. Keep deeper cycle-model refinement scoped to `SPEC-13`, not the top-level eval reports.
