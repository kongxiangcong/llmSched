# Phase 1: Cleanup & Foundation - Context

**Gathered:** 2026-04-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Remove all old v0.9-era code and documentation. Retain only the execution-semantic pipeline infrastructure: ONNX frontend, IR data structures, scheduling core, and the v0.10 descriptor schema docs. Restructure the source tree into domain-focused packages. Update the CLI to a single `compile` command. Rewrite the README for v2 scope.

</domain>

<decisions>
## Implementation Decisions

### Deletion granularity and staging
- **D-01:** Delete whole directories where possible. `src/llm_sched/analysis/` is a wholesale `git rm`. Selective pruning only for `contracts/`, `pipeline/`, `ir/`, and `frontend/`.
- **D-02:** One big cleanup commit for all deletions. Single commit message: `cleanup: remove v0.9-era analysis, diagnosis, visualization, evaluation`.
- **D-03:** `pipeline/descriptor_generation.py` is deleted entirely. Phase 4 creates a new v0.10 descriptor generation module from scratch.
- **D-04:** `pipeline/single_core_scheduling.py` is deleted entirely. Dual-core only; no single-core scenarios.
- **D-05:** `pipeline/performance_estimation.py` is deleted entirely. Phase 6 creates structural metrics output, not cycle-level estimation.
- **D-06:** `docs/development/` and `docs/architecture-diagnosis/` are deleted (`git rm`).
- **D-07:** `docs/plans/` (old execution plan markdown files) is deleted.
- **D-08:** `scripts/run_end_to_end.py` is deleted entirely. Phase 6 or later can create a new end-to-end script when the v2 pipeline is complete.

### CLI shape after cleanup
- **D-09:** Single `compile` command: `llmsched compile model.onnx --config config.yaml --output ./out/`
- **D-10:** Run-root infrastructure (manifests, artifact layouts, run summaries) is replaced with direct output. `compile` writes descriptors + metrics directly to the specified output directory.
- **D-11:** `validate-profile` command is dropped. `compile` validates the config inline.
- **D-12:** Two-profile model (target-profile + scenario-profile) is merged into a single `--config` file. Phase 2 creates the new single-config loader.

### Contracts and IR retention
- **D-13:** `contracts/manifest.py`, `contracts/artifact_layout.py`, and `contracts/run_summary.py` are kept internally as lightweight internal state tracking, even though the CLI no longer exposes run-root commands.
- **D-14:** `ir/descriptor_ir.py` is deleted entirely. Phase 4 creates a new v0.10 DescriptorIR from scratch.
- **D-15:** `config/loader.py` is deleted. Phase 2 creates a new single-config loader.
- **D-16:** `arch/` module is kept and simplified. Single-core paths are removed. Dual-core-only with per-core VMEM. Phase 3 does the scheduling-specific updates.
- **D-17:** `ir/analysis_ir.py` is deleted.
- **D-18:** Remaining contracts are flattened into a single `models.py` module.

### Package structure reorganization
- **D-19:** Restructure `src/llm_sched/` into flat domain packages:
  - `cli.py` (entrypoint, replaces `cli/main.py`)
  - `config.py` (minimal config, Phase 2 expands)
  - `arch.py` (simplified hardware model)
  - `models.py` (flattened Pydantic schemas)
  - `ir/` (`graph.py`, `nig.py`, `schedule.py`, `common.py`, `validators.py`, `io.py`)
  - `frontend/` (`importer.py`, `canonicalize.py`, `nig_lowering.py`, etc.)
  - `scheduler/` (merged from `planning/` + `pipeline/`; `memory.py`, `tile.py`, `dual_core.py`)
  - `descriptor/` (created in Phase 4; `packer.py`, `parser.py`, `verifier.py`)

### Test handling during cleanup
- **D-20:** Delete all old tests now (tests covering deleted modules, and tests for modules that stay but will be rewritten).
- **D-21:** Keep test infrastructure: `tests/conftest.py` and `tests/fixtures/` stay.
- **D-22:** Add a minimal cleanup verification test that asserts old directories/modules are removed and old CLI commands are absent.

### Dependency pruning
- **D-23:** Add `numpy` to dependencies for tensor manipulation during ONNX frontend import.
- **D-24:** Keep Python `>=3.11` in `pyproject.toml`. (PROJECT.md says 3.12+ but 3.11 is sufficient for current needs.)

### README
- **D-25:** Full rewrite with v2 scope. Describe the ONNX → task DAG → scheduling → descriptor packing pipeline, the 6-phase roadmap, and current status. Remove all v0.9-specific content and Chinese text.

### Claude's Discretion
- Exact module names within the new domain packages
- Exact fields preserved in the flattened `models.py`
- Specific content of the cleanup verification test
- Exact simplification applied to `arch.py`

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project requirements and scope
- `.planning/PROJECT.md` — Vision, constraints, key decisions, and out-of-scope table
- `.planning/REQUIREMENTS.md` — CLEAN-01 through CLEAN-04 requirements and traceability
- `.planning/ROADMAP.md` — Phase 1 goal, success criteria, and dependencies

### v0.10 descriptor schema (authoritative)
- `docs/descriptor/family_lut.yaml` — Machine-readable family lookup table
- `docs/descriptor/field_tables.yaml` — Field definitions and bit widths
- `docs/descriptor/layout.yaml` — Record layout and ordering
- `docs/descriptor/descriptor-encoding-layout.md` — Encoding layout specification
- `docs/descriptor/descriptor-family-lut.md` — Family LUT specification
- `docs/descriptor/descriptor-handoff.md` — Handoff documentation

### Source modules to retain (for reference during reorganization)
- `src/llm_sched/frontend/onnx_importer.py` — ONNX import logic (stays, rewritten in Phase 2)
- `src/llm_sched/ir/graph_ir.py` — Graph IR schema (stays)
- `src/llm_sched/ir/nig.py` — NIG IR (stays)
- `src/llm_sched/ir/schedule_ir.py` — Schedule IR (stays)
- `src/llm_sched/ir/common.py` — Shared IR utilities (stays)
- `src/llm_sched/ir/validators.py` — IR validators (stays)
- `src/llm_sched/ir/io.py` — IR serialization (stays)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `GraphIR` / `GraphNode` (Pydantic models in `ir/graph_ir.py`) — Core data structure for the ONNX frontend
- `NIGIR` (in `ir/nig.py`) — Lowered IR, stays for reference during Phase 2/3 rewrites
- `ScheduleIR` (in `ir/schedule_ir.py`) — Scheduling output IR
- `onnx_importer.py` — ONNX loading and shape inference logic stays; macro_op identification added in Phase 2
- `frontend/canonicalize.py` and `frontend/nig_lowering.py` — Canonicalization and lowering logic stays; task-DAG transformation added in Phase 2

### Established Patterns
- Pydantic v2 `BaseModel` with `ConfigDict(extra="forbid")` used throughout
- IR serialization via `model_dump(mode="json")` pattern
- CLI uses Typer with typed Path options
- Pipeline functions return result objects with `status: Literal["completed", "failed"]` and `diagnostics` list

### Integration Points
- `frontend/` → `ir/graph_ir.py` → `ir/nig.py` → scheduling → descriptor packing
- CLI entrypoint currently at `cli/main.py`; will become `cli.py` at package root
- Config loading currently at `config/loader.py`; will become `config.py`

</code_context>

<specifics>
## Specific Ideas

- "Whole directories where possible" — `analysis/` and old docs get wholesale `git rm`
- "One big cleanup commit" — prefer a single commit over staged-by-subsystem
- README should be a complete v2 rewrite, not a minimal placeholder
- Package structure should be flat domain packages (not layered)
- Contracts flattened to a single `models.py` file

</specifics>

<deferred>
## Deferred Ideas

- End-to-end script — Phase 6 or later
- Single-config loader — Phase 2
- v0.10 DescriptorIR — Phase 4
- Structural metrics module — Phase 6
- New smoke tests — written per-phase as modules land

</deferred>

---

*Phase: 01-cleanup-foundation*
*Context gathered: 2026-04-21*
