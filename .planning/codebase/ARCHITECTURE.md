# Architecture

**Analysis Date:** 2026-04-21

## Pattern Overview

**Overall:** Multi-phase compiler pipeline with typed IR progression and artifact-driven execution

**Key Characteristics:**
- Each pipeline phase consumes artifacts from the previous phase and emits new artifacts
- All inter-phase data is serialized as JSON and tracked in a run manifest artifact index
- Pydantic models enforce schema contracts at every boundary (IR, reports, profiles)
- Workflows are deterministic and target-profile-parametric (single-core vs dual-core, prefill vs decode)
- Diagnosis layer sits additive above the core pipeline, consuming finalized artifacts to produce assessment reports

## Layers

**CLI Layer:**
- Purpose: User-facing entrypoints, argument parsing, and orchestration commands
- Location: `src/llm_sched/cli/main.py`
- Contains: Typer commands for every pipeline phase, profile validation, run initialization
- Depends on: Pipeline workflows, config loader, contract models
- Used by: End users, end-to-end runner script

**Pipeline Layer:**
- Purpose: Run-root workflow implementations that load artifacts, invoke planners/analyzers, and persist results
- Location: `src/llm_sched/pipeline/`
- Contains: One workflow module per SPEC phase (frontend_analysis, memory_planning, tile_planning, scheduling, descriptor_generation, performance_estimation, evaluation, diagnosis, visualization, sweep)
- Depends on: IR layer, planning layer, analysis layer, config loader, contracts
- Used by: CLI commands, end-to-end runner, smoke tests

**Planning Layer:**
- Purpose: Core algorithmic implementations for memory planning, tiling, scheduling, and descriptor building
- Location: `src/llm_sched/planning/`
- Contains: memory_planner, tile_planner, single_core_scheduler, dual_core_scheduler, descriptor_builder, descriptor_packer
- Depends on: IR layer, architecture capabilities, config profiles
- Used by: Pipeline workflows

**IR Layer:**
- Purpose: Typed intermediate representations that carry data between pipeline phases
- Location: `src/llm_sched/ir/`
- Contains: graph_ir, nig, schedule_ir, descriptor_ir, analysis_ir, common, io, validators
- Depends on: Pydantic
- Used by: All pipeline and planning modules

**Analysis Layer:**
- Purpose: Report builders that aggregate IR and contract data into human-readable and machine-readable reports
- Location: `src/llm_sched/analysis/`
- Contains: Report builders for every output type (prefill, decode, sweep, diagnosis, visualization, performance, roofline, etc.)
- Depends on: IR layer, contracts, config
- Used by: Pipeline workflows

**Contracts Layer:**
- Purpose: Pydantic schema definitions for all artifacts, reports, and manifest structures
- Location: `src/llm_sched/contracts/`
- Contains: 30+ contract modules covering reports, IR bundles, visualization structures, diagnosis schemas
- Depends on: Pydantic
- Used by: All other layers

**Config Layer:**
- Purpose: Load and validate target/scenario profiles with structured diagnostics
- Location: `src/llm_sched/config/`
- Contains: loader, target_profile, scenario_profile
- Depends on: Pydantic
- Used by: CLI, pipeline workflows, planning layer

**Architecture Layer:**
- Purpose: Typed hardware capability model and constraint validation
- Location: `src/llm_sched/arch/`
- Contains: capabilities, constraints, query_api
- Depends on: Config target_profile
- Used by: Planning layer, pipeline workflows

**Frontend Layer:**
- Purpose: ONNX import, graph canonicalization, NIG lowering, shape binding, legality checks
- Location: `src/llm_sched/frontend/`
- Contains: onnx_importer, canonicalize, nig_lowering, binding, shape_binding, legality, model_metadata
- Depends on: IR layer, config
- Used by: Pipeline frontend_analysis workflow

**Visualization Layer:**
- Purpose: Build static HTML workbenches and cross-run catalogs from artifacts
- Location: `src/llm_sched/visualization/`
- Contains: workbench_builder, catalog_builder, diagnosis_workbench_builder
- Depends on: Contracts, analysis layer
- Used by: Pipeline visualization workflows

**Tools Layer:**
- Purpose: Programmatic end-to-end session orchestration
- Location: `src/llm_sched/tools/`
- Contains: end_to_end_runner
- Depends on: CLI (via subprocess), config
- Used by: Scripts, integration tests

## Data Flow

**Core Compile Flow:**

1. `init-run` creates a run directory with `manifest.json`
2. `run-frontend-analysis` loads ONNX model, produces `graph_ir.json` -> `canonical_graph_ir.json` -> `nig_ir.json` -> `bound_nig_ir.json` + reports
3. `run-memory-planning` consumes `bound_nig_ir.json`, produces `memory_plan.json`
4. `run-tile-planning` consumes `bound_nig_ir.json` + `memory_plan.json`, produces `tiling_plan.json`
5. `run-single-core-scheduling` or `run-dual-core-scheduling` consumes bound NIG + memory_plan + tiling_plan, produces `schedule_ir.json` or `dual_core_schedule_ir.json`
6. `run-descriptor-generation` consumes schedule IR + bound NIG + memory_plan, produces `descriptor_ir.json`, `packed_descriptor_bundle.json`, `isa_coverage_report.json`
7. `run-performance-estimation` consumes descriptor IR + schedule IR, produces `perf_analysis_ir.json`, `perf_summary_report.json`
8. `run-prefill-evaluation` or `run-decode-evaluation` consumes perf artifacts, produces evaluation reports

**Diagnosis Flow (additive):**

1. `run-diagnosis-analysis` reads all prior artifacts, produces `reports/diagnosis/*.json` reports and CSV datasets
2. `run-diagnosis-packaging` aggregates diagnosis reports into `diagnosis_bundle.json`
3. `run-diagnosis-workbench` packages a static HTML workbench under `diagnosis_workbench/`

**Visualization Flow:**

1. `run-visualization-packaging` produces `visualization_bundle.json`
2. `run-visualization-workbench` produces `workbench/index.html`
3. `run-visualization-catalog` produces cross-run `catalog/index.html`

**State Management:**
- Run state is file-system based: each phase reads from and writes JSON artifacts to a run-root directory
- `manifest.json` tracks artifact_index mapping logical names to relative paths
- `run-summary.json` tracks completion status and diagnostics per phase
- No in-memory shared state across phases; phases are independently invokable

## Key Abstractions

**IR Documents:**
- Purpose: Typed, versioned, serializable representations of compiler state
- Examples: `src/llm_sched/ir/graph_ir.py`, `src/llm_sched/ir/nig.py`, `src/llm_sched/ir/schedule_ir.py`, `src/llm_sched/ir/descriptor_ir.py`
- Pattern: Pydantic BaseModel with `ConfigDict(extra="forbid")`, model validators for invariants, `ir_version` and `graph_id` fields

**Run Manifest:**
- Purpose: Central registry for a single run's inputs and artifacts
- Examples: `src/llm_sched/contracts/manifest.py`
- Pattern: Pydantic model with `artifact_index: dict[str, str]` mapping logical artifact names to relative file paths

**Artifact Layout:**
- Purpose: Canonical directory structure for run outputs
- Examples: `src/llm_sched/contracts/artifact_layout.py`
- Pattern: `build_run_layout(run_root)` returns paths for `artifacts/`, `reports/`, `logs/`, `dumps/`

**Profile-Driven Parametrization:**
- Purpose: All planning decisions are driven by target hardware profiles and scenario profiles
- Examples: `src/llm_sched/config/target_profile.py`, `src/llm_sched/config/scenario_profile.py`
- Pattern: Pydantic-validated JSON profiles loaded at runtime; `ArchitectureCapabilities` derived from target profile

**Pipeline Result Pattern:**
- Purpose: Uniform success/failure representation for every workflow
- Examples: `FrontendAnalysisResult`, `MemoryPlanningResult`, `SingleCoreSchedulingResult` in respective pipeline modules
- Pattern: Pydantic BaseModel with `status: Literal["completed", "failed"]`, optional output paths, and `diagnostics: list[Diagnostic]`

## Entry Points

**CLI Application:**
- Location: `src/llm_sched/cli/main.py`
- Triggers: Direct invocation via `python -m llm_sched.cli.main <command>`
- Responsibilities: Parse arguments, validate profiles, dispatch to pipeline workflows, emit exit codes

**End-to-End Runner:**
- Location: `src/llm_sched/tools/end_to_end_runner.py`
- Triggers: `scripts/run_end_to_end.py` or programmatic `run_end_to_end_session(plan)`
- Responsibilities: Build a session plan, orchestrate full pipeline via CLI subprocess calls, collect logs, emit session summary

**Package Import:**
- Location: `src/llm_sched/__init__.py` (minimal), `src/llm_sched/pipeline/__init__.py` (exports all workflow functions)
- Triggers: `from llm_sched.pipeline import run_frontend_analysis`
- Responsibilities: Expose workflow functions for programmatic use and testing

## Error Handling

**Strategy:** Exceptions are caught at the pipeline workflow boundary, converted to diagnostics, and recorded in `run-summary.json` and the manifest. The CLI exits with code 1 on failure.

**Patterns:**
- Each pipeline workflow wraps its body in a try/except that catches `Exception`
- `FileNotFoundError` on `manifest.json` is given a special diagnostic message
- Profile loading raises `MalformedProfileError` or `ProfileValidationFailure` with structured `Diagnostic` lists
- IR validators use Pydantic `model_validator(mode="after")` to enforce invariants at deserialization time

## Cross-Cutting Concerns

**Logging:** Console output via `typer.echo` in CLI; per-phase stdout/stderr captured to `logs/*.log` files by the end-to-end runner

**Validation:** Pydantic models enforce schemas at every boundary. IR validators (`src/llm_sched/ir/validators.py`) provide explicit validation entrypoints. Profile loader validates JSON against typed schemas.

**Authentication:** Not applicable - local CLI tool with no network authentication

**Traceability:** Every IR node and schedule block carries an `AuditRef` (`src/llm_sched/ir/common.py`) linking graph_node_ids, nig_node_ids, schedule_block_ids, descriptor_ids, and source_ids for cross-layer debugging.

---

*Architecture analysis: 2026-04-21*
