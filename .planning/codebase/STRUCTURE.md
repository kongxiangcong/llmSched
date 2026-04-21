# Codebase Structure

**Analysis Date:** 2026-04-21

## Directory Layout

```
/home/ubuntu/llmSched/
├── src/llm_sched/           # Main source package
│   ├── cli/                 # CLI entrypoint (Typer)
│   ├── pipeline/            # Run-root workflow implementations
│   ├── planning/            # Core algorithms (memory, tile, schedule, descriptor)
│   ├── ir/                  # Intermediate representations (Graph, NIG, Schedule, Descriptor, Analysis)
│   ├── analysis/            # Report builders and estimators
│   ├── contracts/           # Pydantic schemas for all artifacts and reports
│   ├── config/              # Profile loading and validation
│   ├── arch/                # Hardware capability models and constraint checks
│   ├── frontend/            # ONNX import, canonicalization, lowering, binding
│   ├── visualization/       # Static HTML workbench and catalog builders
│   └── tools/               # End-to-end runner and orchestration helpers
├── tests/
│   ├── unit/                # Unit tests mirroring src structure
│   ├── smoke/               # CLI smoke tests for each command
│   └── fixtures/            # Baseline artifacts for diagnosis tests
├── profiles/
│   ├── targets/             # Hardware target profiles (JSON)
│   └── scenarios/           # Workload scenario profiles (JSON)
├── scripts/                 # Repo-local runner scripts
├── inputs/                  # Model inputs (e.g., gemma3_1b ONNX)
├── docs/                    # Documentation and planning docs
├── pyproject.toml           # Project metadata and dependencies
└── uv.lock                  # Dependency lockfile
```

## Directory Purposes

**`src/llm_sched/cli/`:**
- Purpose: User-facing CLI commands
- Contains: `main.py` with all Typer commands
- Key files: `src/llm_sched/cli/main.py`

**`src/llm_sched/pipeline/`:**
- Purpose: Workflow entrypoints that orchestrate each SPEC phase
- Contains: 20+ workflow modules, one per CLI command
- Key files: `frontend_analysis.py`, `memory_planning.py`, `single_core_scheduling.py`, `dual_core_scheduling.py`, `diagnosis_analysis.py`, `visualization_catalog.py`

**`src/llm_sched/planning/`:**
- Purpose: Core algorithm implementations
- Contains: Memory planner, tile planner, single/dual core schedulers, descriptor builder/packer
- Key files: `memory_planner.py`, `tile_planner.py`, `single_core_scheduler.py`, `dual_core_scheduler.py`, `descriptor_builder.py`, `descriptor_packer.py`

**`src/llm_sched/ir/`:**
- Purpose: Typed intermediate representations
- Contains: Schema definitions for GraphIR, NIGIR, ScheduleIR, DescriptorIR, AnalysisIR, plus serialization helpers
- Key files: `graph_ir.py`, `nig.py`, `schedule_ir.py`, `descriptor_ir.py`, `io.py`, `validators.py`

**`src/llm_sched/analysis/`:**
- Purpose: Report generation and data aggregation
- Contains: 20+ report builder modules covering evaluation, diagnosis, visualization, sweep
- Key files: `descriptor_estimator.py`, `visualization_bundle_builder.py`, `sweep_report_builder.py`, `performance_diagnostics_report_builder.py`

**`src/llm_sched/contracts/`:**
- Purpose: Schema definitions for all artifacts
- Contains: 30+ Pydantic model modules for reports, IR bundles, diagnosis structures
- Key files: `manifest.py`, `artifact_layout.py`, `memory_plan.py`, `sweep_report.py`, `visualization_bundle.py`

**`src/llm_sched/config/`:**
- Purpose: Profile loading and diagnostic reporting
- Contains: Loader, target profile schema, scenario profile schema
- Key files: `loader.py`, `target_profile.py`, `scenario_profile.py`

**`src/llm_sched/arch/`:**
- Purpose: Hardware abstraction and constraint validation
- Contains: Capability model, constraint checker, query API
- Key files: `capabilities.py`, `constraints.py`, `query_api.py`

**`src/llm_sched/frontend/`:**
- Purpose: Model import and graph transformation
- Contains: ONNX importer, canonicalizer, NIG lowerer, shape binder, legality checker
- Key files: `onnx_importer.py`, `canonicalize.py`, `nig_lowering.py`, `binding.py`, `shape_binding.py`

**`src/llm_sched/visualization/`:**
- Purpose: Static HTML artifact generation
- Contains: Workbench builder, catalog builder, diagnosis workbench builder
- Key files: `workbench_builder.py`, `catalog_builder.py`, `diagnosis_workbench_builder.py`

**`src/llm_sched/tools/`:**
- Purpose: Programmatic orchestration
- Contains: End-to-end runner that drives CLI via subprocess
- Key files: `end_to_end_runner.py`

**`tests/unit/`:**
- Purpose: Fast, focused unit tests
- Contains: Mirrors `src/llm_sched/` structure with `test_*.py` files
- Key files: `tests/unit/planning/`, `tests/unit/pipeline/`, `tests/unit/contracts/`, `tests/unit/ir/`

**`tests/smoke/`:**
- Purpose: CLI integration smoke tests
- Contains: One test per CLI command, plus matrix tests for phase acceptance
- Key files: `test_cli_run_*.py`, `test_phase_*_matrix.py`

**`tests/fixtures/`:**
- Purpose: Baseline artifacts for diagnosis tests
- Contains: Pre-generated diagnosis reports and datasets for single/dual core prefill/decode
- Key files: `diagnosis_baseline/index.json`

**`profiles/`:**
- Purpose: JSON configuration files for hardware targets and workload scenarios
- Contains: `targets/riscv_npu_single_core_v1.json`, `targets/riscv_npu_dual_core_v1.json`, `scenarios/prefill_seq128.json`, `scenarios/decode_token1_kv2048.json`

## Key File Locations

**Entry Points:**
- `src/llm_sched/cli/main.py`: Main CLI application
- `scripts/run_end_to_end.py`: Convenience script for full pipeline execution
- `src/llm_sched/tools/end_to_end_runner.py`: Programmatic end-to-end orchestration

**Configuration:**
- `pyproject.toml`: Project metadata, dependencies, pytest config
- `profiles/targets/riscv_npu_single_core_v1.json`: Single-core hardware profile
- `profiles/targets/riscv_npu_dual_core_v1.json`: Dual-core hardware profile
- `profiles/scenarios/prefill_seq128.json`: Prefill scenario profile
- `profiles/scenarios/decode_token1_kv2048.json`: Decode scenario profile

**Core Logic:**
- `src/llm_sched/planning/memory_planner.py`: Static VMEM / KV memory planning
- `src/llm_sched/planning/tile_planner.py`: Tile candidate generation
- `src/llm_sched/planning/single_core_scheduler.py`: Deterministic single-core scheduling
- `src/llm_sched/planning/dual_core_scheduler.py`: Deterministic dual-core scheduling with overlap
- `src/llm_sched/planning/descriptor_builder.py`: Schedule-to-descriptor mapping
- `src/llm_sched/planning/descriptor_packer.py`: 512-bit descriptor packing

**Testing:**
- `tests/conftest.py`: Shared pytest fixtures
- `tests/smoke/conftest.py`: Smoke-test specific fixtures
- `tests/unit/pipeline/conftest.py`: Pipeline test fixtures

## Naming Conventions

**Files:**
- Modules use `snake_case.py`
- Test files use `test_<module_name>.py`
- Report builder modules use `<report_name>_report_builder.py`
- Contract modules use `<artifact_name>.py`

**Directories:**
- Package directories match module namespaces: `llm_sched/pipeline/`, `llm_sched/planning/`
- Test directories mirror source structure: `tests/unit/pipeline/`, `tests/unit/planning/`

**Classes:**
- IR models use suffix `IR` (e.g., `GraphIR`, `NIGIR`, `ScheduleIR`)
- Report models use suffix `Report` (e.g., `PrefillEvaluationReport`, `SweepDeltaReport`)
- Result types use suffix `Result` (e.g., `FrontendAnalysisResult`, `MemoryPlanningResult`)
- Internal dataclasses use leading underscore (e.g., `_PendingBlock`, `_TransferPlan`)

**Functions:**
- Workflow entrypoints use `run_<phase_name>` (e.g., `run_frontend_analysis`, `run_memory_planning`)
- Report builders use `build_<report_name>_report` (e.g., `build_prefill_evaluation_report`)
- Planners use `plan_<artifact>` (e.g., `plan_memory_artifact`, `plan_single_core_schedule`)

## Where to Add New Code

**New Pipeline Phase:**
- Workflow: `src/llm_sched/pipeline/<phase_name>.py`
- Export: `src/llm_sched/pipeline/__init__.py`
- CLI command: `src/llm_sched/cli/main.py`
- Smoke test: `tests/smoke/test_cli_run_<phase_name>.py`
- Unit test: `tests/unit/pipeline/test_<phase_name>_workflow.py`

**New Report Type:**
- Contract schema: `src/llm_sched/contracts/<report_name>.py`
- Export: `src/llm_sched/contracts/__init__.py`
- Builder: `src/llm_sched/analysis/<report_name>_report_builder.py`
- Export: `src/llm_sched/analysis/__init__.py`
- Unit test: `tests/unit/analysis/test_<report_name>_report_builder.py`
- Contract test: `tests/unit/contracts/test_<report_name>.py`

**New IR Type:**
- Schema: `src/llm_sched/ir/<name>_ir.py`
- Export: `src/llm_sched/ir/__init__.py`
- Validator: `src/llm_sched/ir/validators.py`
- Unit test: `tests/unit/ir/test_<name>_ir_invariants.py`

**New Planner/Algorithm:**
- Implementation: `src/llm_sched/planning/<name>.py`
- Export: `src/llm_sched/planning/__init__.py`
- Unit test: `tests/unit/planning/test_<name>.py`

**New Contract/Artifact Schema:**
- Schema: `src/llm_sched/contracts/<artifact_name>.py`
- Export: `src/llm_sched/contracts/__init__.py`
- Unit test: `tests/unit/contracts/test_<artifact_name>.py`

**Utilities:**
- Shared helpers: Add to the most specific existing module; if truly generic, add to `src/llm_sched/ir/common.py` or create a new `src/llm_sched/utils/` package

## Special Directories

**`tests/fixtures/diagnosis_baseline/`:**
- Purpose: Pre-generated diagnosis artifacts for 4 run configurations (single/dual x prefill/decode)
- Generated: Yes (by running the full pipeline)
- Committed: Yes (used as baselines for diagnosis tests)

**`inputs/gemma3_1b/`:**
- Purpose: Model input files (ONNX, config.json)
- Generated: No (external input)
- Committed: No (listed in .gitignore; present locally)

**`.planning/`:**
- Purpose: GSD planning documents and codebase maps
- Generated: No
- Committed: No (planning artifacts, not source code)

---

*Structure analysis: 2026-04-21*
