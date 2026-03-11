# Phase C / M2 Closure Audit

**Date:** 2026-03-11

**Goal:** Re-audit `SPEC-08~12` after the recent schedule-fidelity and packed-descriptor hardening batches, so the remaining `M2` backlog is expressed as a narrow closure list instead of a generic "Phase C still in progress" label.

## Current Judgment

- `Phase C` is still the active project gate.
- `M2` is still `in_progress`.
- The blocking work is no longer "missing foundation".
- The blocking work is now a narrow closure problem across:
  - `SPEC-08`: planner closure and stronger downstream use of the memory artifact
  - `SPEC-09`: deciding whether current tiling coverage is enough, or whether more macro families must produce candidates before `M2` can close
  - `SPEC-10/11`: remaining generic reservation surfaces
  - `SPEC-12`: deciding and freezing the actual Phase C stop-line for packed-descriptor fidelity

## 2026-03-11 Execution Update

- `ELEM_ADD.store` has now been audited directly instead of staying on the generic-risk list.
- New executed evidence:
  - focused single-core and dual-core red tests both failed first with `follower_issue == 4`, proving `ELEM_ADD.store` still behaved like one monolithic shared-`DMA` slab
  - `schedule_duration.py` now gives `ELEM_ADD.store` a short internal `VPU` prefix before the later `DMA` writeback window while the public stage model stays unchanged
  - focused `store_issue_with_vpu_prefix` regression now passes at `16 passed`
  - full single-core plus dual-core scheduler unit slices now pass at `60 passed`
- Explicit closure decisions now taken:
  - `SPEC-09`: accept the current GEMM-like plus attention tiling surface for `M2`, with untiled-helper scheduling as the accepted policy unless a concrete failing consumer proves broader macro tiling is required
  - `SPEC-12`: freeze the `M2` stop-line at packed summary consumer proof plus workbench summary visibility; do not add per-record drilldown unless a concrete consumer requires it

## Evidence Summary

### SPEC-08

- `MemoryPlanArtifact` now exposes:
  - `storage_bindings`
  - `storage_binding_id`
  - `backing_store`
  - `peak_bytes_by_memory_class`
  - `peak_bytes_by_backing_store`
- This is real progress, and the memory planner already computes and validates those fields.
- But the current downstream usage is still narrow:
  - `tile_planner.py` consumes `memory_plan.storage_bindings`
  - the audit did not find corresponding downstream consumption in descriptor generation or later analysis layers

**Conclusion:** `SPEC-08` is no longer blocked on "missing external-memory semantics". The remaining gap is planner closure plus stronger downstream consumption, not more contract invention.

### SPEC-09

- `tile_planner.py` still only builds candidates for:
  - GEMM-like macros
  - attention macros
- Untiled helper macros are handled later by scheduler fallback rather than by a broader tiling surface.

**Conclusion:** the real open question is no longer "can tiling run at all?" but "does `M2` require broader candidate generation, or is the current untiled-helper policy sufficient for closure?" That decision should be made explicitly.

### SPEC-10 / SPEC-11

- Scheduler fidelity has materially improved:
  - mixed-engine compute phasing exists
  - several `dma_in` surfaces now expose `DMA + tail`
  - several `store` surfaces now expose `VPU prefix + DMA writeback`
- But the current specialization set is still selective.
- In `single_core_scheduler.py`, macros such as `RMSNORM`, `ELEM_ADD`, and `GEGLU` still present `store = ["DMA"]` at the public stage-policy layer.
- In `schedule_duration.py`, `store/dma_in` specialization covers only a subset of those surfaces.

**Conclusion:** `SPEC-10/11` is now in a true closure phase. The next work should be evidence-driven audits of remaining generic reservation surfaces, not another broad exploration cycle.

### SPEC-12

- `SPEC-12` now has:
  - deterministic field ordering
  - specialized DMA / transfer templates
  - packed stream/container metadata
  - visualization packaging consumption
  - workbench coverage-panel visibility
- But compute descriptor packing still stays generic for most compute opcodes:
  - `descriptor_builder.py` still maps most compute descriptors to `tensor_compute_v1`
  - only narrow opcode families have stronger template specialization today

**Conclusion:** `SPEC-12` no longer looks like the sharpest unresolved Phase C risk. The remaining work is not "invent more consumers"; it is deciding whether the current summary-grade ABI proof is already enough for `M2`, or whether one more opcode-family / field-placement batch is truly required.

## Recommended Closure List

### P0

- Run one narrow scheduler audit batch on remaining generic reservation surfaces:
  - `RMSNORM.store`
  - `ELEM_ADD.store`
  - `GEGLU.store`
- Only implement a new specialization when a focused red/green test proves a real fidelity gap.

### P1

- Make an explicit `SPEC-09` closure decision:
  - either broaden tiling coverage beyond GEMM/attention
  - or document that untiled-helper scheduling is the accepted `M2` policy for the current compiler scope

### P2

- Freeze the `SPEC-12` stop-line for `M2`.
- Recommended stop-line:
  - packed summary consumer proof is enough
  - workbench summary visibility is enough
  - do not add per-record drilldown unless a concrete consumer requirement appears

### P3

- After the three decisions above, run a final Phase C closure pass and rewrite the `SPEC-08~12` status lines from "broad remaining gap" to a short explicit acceptance list.

## What Not To Do Next

- Do not reopen frontend work.
- Do not keep expanding visualization UI unless it closes a real `SPEC-12` acceptance gap.
- Do not keep adding schedule specializations without a failing test first.
- Do not keep describing `SPEC-08` as if storage semantics were still missing; the contracts are already there.

## Outcome

- The current `M2` backlog is now narrow and concrete.
- The strongest next direction is back on `SPEC-10/11`, but only as an evidence-driven closure pass.
- `SPEC-12` should remain a targeted hardening track, not the sole mainline.
- The former `SPEC-09` and `SPEC-12` ambiguity has been reduced to an accepted scope boundary rather than an open design question.
