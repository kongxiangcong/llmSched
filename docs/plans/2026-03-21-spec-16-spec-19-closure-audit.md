# 2026-03-21 SPEC-16 / SPEC-19 Closure Audit

## Goal

Reclassify the remaining work near project close so the team can distinguish:

- true blockers to closing the current `SPEC-16` mainline
- near-done follow-ons that strengthen the same mainline
- downstream `SPEC-19` polish that should not keep the project open by itself

## Current Read

### What now looks effectively closed on the current `SPEC-16` recommendation-detail track

- catalog/workbench recommendation queues are continuous
- dedicated sweep deep links preserve queue context
- workbench exposes:
  - top recommendation compare strip
  - recommendation detail blocks
  - multi-candidate export/snapshot continuity
- catalog workspace now mirrors that richer recommendation-detail continuity
- recommendation-detail summaries and renderers now have shared snippet-level convergence across catalog/workbench

### What still looks like real `SPEC-16` closure work

- one last compare-interaction audit to decide whether the current richer recommendation-detail surface is already enough as the practical stop-line for this branch of `SPEC-16`
- if not enough, only one additional slice should be considered mainline-worthy:
  - a small, explicit multi-candidate compare closure slice that materially improves analyst decision-making beyond current recommendation detail blocks

### What no longer looks like a blocker

- queue continuity hardening
- richer recommendation-detail export continuity
- catalog/workbench parity for top-candidate detail summaries
- local helper duplication cleanup within the recommendation-detail flow

## Recommended Close-Out Classification

### P0: true blocker before calling the current `SPEC-16` recommendation-detail track “closed enough”

- perform one explicit closure pass on current compare UX:
  - confirm whether analysts can answer “which candidate should I inspect next, and why?” without reopening raw bundle JSON or manually walking the sweep table
  - if yes, freeze this sub-track and stop adding more recommendation-detail features by default
  - if no, allow exactly one final focused slice, not another open-ended interaction batch

### P1: near-done but optional if P0 says “good enough”

- tighten wording, labels, and snapshot naming around recommendation-detail surfaces
- trim any remaining catalog/workbench presentation asymmetry that does not require new payload fields

### P2: pure downstream polish, should not block close-out

- richer screenshot workflow
- broader visual polish on static surfaces
- any new `SPEC-19` convenience interaction that does not change closure confidence for current compare work

## Recommended Next Execution Order

1. run the closure pass on current `SPEC-16` recommendation-detail usability
2. if closure pass says “enough”, freeze this sub-track and shift the main conversation to the remaining non-recommendation `SPEC-16` / `SPEC-13/14/15` gaps
3. only after that, return to `SPEC-19` polish as a downstream hardening queue

## Practical Stop-Line Recommendation

For the current recommendation-detail branch, the stop-line should be:

- queue-aware catalog/workbench continuity exists
- top recommendations can be inspected side-by-side
- richer candidate detail survives export/snapshot paths
- catalog/workbench share the same recommendation-detail semantics and renderer structure

That stop-line is now effectively present.

## Suggested Interpretation

The right next move is not “invent one more recommendation-detail enhancement by default”.

The right next move is:

- declare this branch of `SPEC-16` near-closed
- audit whether one final compare-interaction gap remains
- otherwise move back up one level and reassess the remaining true project blockers

## Final Decision

Decision: close-enough

- stop-line audit: `pass`
  - queue-aware catalog/workbench continuity: `pass`
  - side-by-side top recommendation inspection: `pass`
  - richer recommendation detail in page UI: `pass`
  - recommendation detail export/snapshot continuity: `pass`
  - shared recommendation-detail semantics across catalog/workbench: `pass`
- analyst-closure audit: `pass`
  - analysts can tell which candidate to inspect next from the recommendation queue and top recommendation surfaces
  - analysts can see why that candidate is recommended from the compare strip plus recommendation detail summaries
  - analysts can inspect deeper detail without reopening raw bundle JSON because detail blocks are already exposed in catalog/workbench
  - analysts can preserve that context through JSON/SVG export and snapshot metadata/text
- fresh verification evidence remains green:
  - `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q` -> `20 passed`
  - `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q` -> `28 passed`

Exact next action:

- freeze the current `SPEC-16` recommendation-detail branch as a practical stop-line
- move the blocker review back to the remaining broader `SPEC-16` / `SPEC-13/14/15` gaps
- keep `SPEC-19` classified as downstream polish only
