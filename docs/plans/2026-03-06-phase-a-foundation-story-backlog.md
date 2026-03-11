# Phase A Foundation Story Backlog

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the Phase A foundation for the evaluation compiler by turning `SPEC-01` / `SPEC-02` / `SPEC-05` / `SPEC-06` into directly executable stories.

**Architecture:** Use a Python-first foundation optimized for fast iteration: versioned JSON profile contracts, a thin CLI driver, a reusable architecture capability model, and strongly validated IR schemas. Phase A explicitly stops before model import, graph lowering, tiling, or scheduling logic; it only creates the contracts and runtime skeleton those later phases depend on.

**Tech Stack:** Python 3.11+, `pydantic`, `typer`, `pytest`, JSON artifacts, Markdown docs.

---

## Scope and Assumptions

- The implementation language for MVP is assumed to be Python because this project prioritizes modeling speed, iteration speed, and report generation over low-level runtime efficiency.
- Profile files are JSON in Phase A to minimize parser complexity and make schema validation straightforward.
- The package root below assumes `src/llm_sched/`.
- Phase A deliverables must be runnable without implementing model import, scheduling, or descriptor generation.

## Recommended Repository Skeleton

**Create in Phase A:**

- `pyproject.toml`
- `src/llm_sched/__init__.py`
- `src/llm_sched/cli/__init__.py`
- `src/llm_sched/cli/main.py`
- `src/llm_sched/config/__init__.py`
- `src/llm_sched/config/target_profile.py`
- `src/llm_sched/config/scenario_profile.py`
- `src/llm_sched/config/loader.py`
- `src/llm_sched/contracts/__init__.py`
- `src/llm_sched/contracts/manifest.py`
- `src/llm_sched/contracts/artifact_layout.py`
- `src/llm_sched/arch/__init__.py`
- `src/llm_sched/arch/capabilities.py`
- `src/llm_sched/arch/constraints.py`
- `src/llm_sched/arch/query_api.py`
- `src/llm_sched/ir/__init__.py`
- `src/llm_sched/ir/graph_ir.py`
- `src/llm_sched/ir/nig.py`
- `src/llm_sched/ir/schedule_ir.py`
- `src/llm_sched/ir/descriptor_ir.py`
- `src/llm_sched/ir/analysis_ir.py`
- `src/llm_sched/ir/validators.py`
- `src/llm_sched/ir/io.py`
- `profiles/targets/riscv_npu_single_core_v1.json`
- `profiles/targets/riscv_npu_dual_core_v1.json`
- `profiles/scenarios/prefill_seq128.json`
- `profiles/scenarios/decode_token1_kv2048.json`
- `tests/unit/config/`
- `tests/unit/contracts/`
- `tests/unit/arch/`
- `tests/unit/ir/`
- `tests/smoke/`

## Backlog Overview

| Story ID | Spec | Title | Priority | Depends On |
| --- | --- | --- | --- | --- |
| PHA-01 | SPEC-02 | Bootstrap package and CLI shell | P0 | None |
| PHA-02 | SPEC-01 | Define target profile schema | P0 | PHA-01 |
| PHA-03 | SPEC-01 | Define scenario profile schema | P0 | PHA-01 |
| PHA-04 | SPEC-01 | Build profile loader and diagnostics | P0 | PHA-02, PHA-03 |
| PHA-05 | SPEC-01, SPEC-05 | Add canonical hardware and scenario fixtures | P0 | PHA-04 |
| PHA-06 | SPEC-02 | Define run manifest and artifact directory contract | P0 | PHA-01, PHA-04 |
| PHA-07 | SPEC-02 | Add CLI commands for validate and init-run | P0 | PHA-04, PHA-06 |
| PHA-08 | SPEC-02 | Add logging, error code, and run summary contract | P1 | PHA-07 |
| PHA-09 | SPEC-05 | Implement architecture capability model | P0 | PHA-02, PHA-05 |
| PHA-10 | SPEC-05 | Implement hard-constraint checker | P0 | PHA-09 |
| PHA-11 | SPEC-05 | Expose planner-facing architecture query API | P1 | PHA-09, PHA-10 |
| PHA-12 | SPEC-06 | Define IR schemas and versioned validators | P0 | PHA-01, PHA-09 |
| PHA-13 | SPEC-06 | Add IR traceability and audit reference contract | P1 | PHA-12 |
| PHA-14 | SPEC-06 | Add IR serialization, dump, and reload contract | P1 | PHA-12, PHA-13, PHA-06 |
| PHA-15 | SPEC-06 | Build invariant regression suite for all IR layers | P0 | PHA-12, PHA-14 |
| PHA-16 | SPEC-01, SPEC-02, SPEC-05, SPEC-06 | Publish Phase A smoke flow and handoff docs | P1 | PHA-05, PHA-08, PHA-11, PHA-15 |

## Detailed Stories

### Story PHA-01: Bootstrap package and CLI shell

**Spec:** `SPEC-02`

**Goal:** Create the minimum Python package, dependency definition, and CLI entrypoint so later stories share one executable surface.

**Files:**
- Create: `pyproject.toml`
- Create: `src/llm_sched/__init__.py`
- Create: `src/llm_sched/cli/__init__.py`
- Create: `src/llm_sched/cli/main.py`
- Create: `tests/smoke/test_cli_help.py`

**Deliverables:**
- Installable package skeleton.
- A `llm-sched` CLI with placeholder subcommands for `validate-profile` and `init-run`.
- Smoke test that verifies the CLI boots.

**Acceptance:**
- Run: `python -m pytest tests/smoke/test_cli_help.py -v`
- Expected: CLI help renders and process exits with code `0`.
- Run: `python -m llm_sched.cli.main --help`
- Expected: top-level command lists `validate-profile` and `init-run`.

### Story PHA-02: Define target profile schema

**Spec:** `SPEC-01`

**Goal:** Freeze the JSON schema for hardware target profiles so all later modules depend on one canonical representation.

**Files:**
- Create: `src/llm_sched/config/target_profile.py`
- Create: `tests/unit/config/test_target_profile_schema.py`

**Deliverables:**
- Typed target profile model.
- Required fields for `core_mode`, DMA bandwidth, VMEM layout, opcode availability, quant capabilities, sync costs, and architectural constraints.
- Clear validation errors for missing or conflicting fields.

**Depends On:** `PHA-01`

**Acceptance:**
- Run: `python -m pytest tests/unit/config/test_target_profile_schema.py -v`
- Expected: valid fixture loads; invalid fixtures fail with deterministic messages.
- Target profile must distinguish `single-core` and `dual-core` without ambiguous defaults.

### Story PHA-03: Define scenario profile schema

**Spec:** `SPEC-01`

**Goal:** Freeze the JSON schema for workload scenarios so `prefill` and `decode` can be expressed without embedding scenario assumptions in code.

**Files:**
- Create: `src/llm_sched/config/scenario_profile.py`
- Create: `tests/unit/config/test_scenario_profile_schema.py`

**Deliverables:**
- Typed scenario profile model.
- Required fields for `mode`, `batch`, `seq_len`, `kv_len`, `layer_scope`, and reporting options.
- Validation rules that reject impossible combinations, such as `decode` with `seq_len > 1` when `S_q = 1` is required.

**Depends On:** `PHA-01`

**Acceptance:**
- Run: `python -m pytest tests/unit/config/test_scenario_profile_schema.py -v`
- Expected: valid prefill and decode fixtures load; invalid mode/shape combinations fail.

### Story PHA-04: Build profile loader and diagnostics

**Spec:** `SPEC-01`

**Goal:** Provide one loader that resolves target/scenario JSON, validates them, and emits structured diagnostics.

**Files:**
- Create: `src/llm_sched/config/loader.py`
- Create: `tests/unit/config/test_profile_loader.py`

**Deliverables:**
- File loader for target and scenario profiles.
- Unified diagnostics object with path, field, severity, and human-readable message.
- Stable API consumed by CLI and later compilers.

**Depends On:** `PHA-02`, `PHA-03`

**Acceptance:**
- Run: `python -m pytest tests/unit/config/test_profile_loader.py -v`
- Expected: loader returns typed models on success and structured diagnostics on failure.
- Missing file, malformed JSON, and schema violation must produce distinct error classes.

### Story PHA-05: Add canonical hardware and scenario fixtures

**Spec:** `SPEC-01`, `SPEC-05`

**Goal:** Check in the minimal canonical fixtures that represent the current RISC-V + NPU architecture assumptions and two baseline scenarios.

**Files:**
- Create: `profiles/targets/riscv_npu_single_core_v1.json`
- Create: `profiles/targets/riscv_npu_dual_core_v1.json`
- Create: `profiles/scenarios/prefill_seq128.json`
- Create: `profiles/scenarios/decode_token1_kv2048.json`
- Create: `tests/unit/config/test_profile_fixtures.py`

**Deliverables:**
- One single-core target profile.
- One dual-core target profile.
- One baseline prefill scenario.
- One baseline decode scenario.

**Depends On:** `PHA-04`

**Acceptance:**
- Run: `python -m pytest tests/unit/config/test_profile_fixtures.py -v`
- Expected: all checked-in fixtures load successfully through the public loader.
- Dual-core fixture must encode shared DMA and cross-core capabilities explicitly.

### Story PHA-06: Define run manifest and artifact directory contract

**Spec:** `SPEC-02`

**Goal:** Freeze the structure of one evaluation run so every later phase writes outputs into a predictable contract.

**Files:**
- Create: `src/llm_sched/contracts/manifest.py`
- Create: `src/llm_sched/contracts/artifact_layout.py`
- Create: `tests/unit/contracts/test_manifest_contract.py`

**Deliverables:**
- Manifest schema containing run id, timestamps, model path, target profile path, scenario profile path, artifact index, and status.
- Canonical directory layout for `artifacts/`, `reports/`, `logs/`, and `dumps/`.
- Versioned contract string for forward compatibility.

**Depends On:** `PHA-01`, `PHA-04`

**Acceptance:**
- Run: `python -m pytest tests/unit/contracts/test_manifest_contract.py -v`
- Expected: manifest serializes/deserializes and artifact paths resolve deterministically from a run root.

### Story PHA-07: Add CLI commands for validate and init-run

**Spec:** `SPEC-02`

**Goal:** Make the Phase A contract usable from the terminal before any compiler logic exists.

**Files:**
- Modify: `src/llm_sched/cli/main.py`
- Create: `tests/smoke/test_cli_validate_profile.py`
- Create: `tests/smoke/test_cli_init_run.py`

**Deliverables:**
- `validate-profile` command for target/scenario JSON.
- `init-run` command that creates the run directory and writes an initial manifest.
- User-visible help text explaining required inputs and outputs.

**Depends On:** `PHA-04`, `PHA-06`

**Acceptance:**
- Run: `python -m pytest tests/smoke/test_cli_validate_profile.py tests/smoke/test_cli_init_run.py -v`
- Expected: valid profiles pass; invalid profiles return non-zero; run root is created with manifest.

### Story PHA-08: Add logging, error code, and run summary contract

**Spec:** `SPEC-02`

**Goal:** Ensure every Phase A command emits predictable logs and machine-readable failure summaries.

**Files:**
- Create: `src/llm_sched/contracts/run_summary.py`
- Modify: `src/llm_sched/cli/main.py`
- Create: `tests/unit/contracts/test_run_summary.py`

**Deliverables:**
- Structured run summary file.
- Exit code map for success, validation failure, contract failure, and unexpected error.
- Log format stable enough for later UI ingestion.

**Depends On:** `PHA-07`

**Acceptance:**
- Run: `python -m pytest tests/unit/contracts/test_run_summary.py -v`
- Expected: summary file records status, diagnostics, and manifest pointer; exit codes are stable.

### Story PHA-09: Implement architecture capability model

**Spec:** `SPEC-05`

**Goal:** Represent the hardware as a typed capability object that later planners can query without parsing raw JSON themselves.

**Files:**
- Create: `src/llm_sched/arch/capabilities.py`
- Create: `tests/unit/arch/test_capabilities_model.py`

**Deliverables:**
- Capability model for core topology, DMA, VPU, MXU, WDQ, VMEM, KV, cross-core link, and opcode availability.
- Constructor from target profile.
- Stable names for resources and hard boundaries.

**Depends On:** `PHA-02`, `PHA-05`

**Acceptance:**
- Run: `python -m pytest tests/unit/arch/test_capabilities_model.py -v`
- Expected: single-core and dual-core profiles both build capability objects with correct resource counts and flags.

### Story PHA-10: Implement hard-constraint checker

**Spec:** `SPEC-05`

**Goal:** Reject impossible mappings early by encoding architecture rules as explicit constraint checks.

**Files:**
- Create: `src/llm_sched/arch/constraints.py`
- Create: `tests/unit/arch/test_constraints.py`

**Deliverables:**
- Rule checks for DMA-only external memory access, `VPU -> MXU` control ownership, NoC exclusion from intra-accelerator traffic, VMEM region legality, and `single-core` / `dual-core` mode constraints.
- Structured constraint violation diagnostics.

**Depends On:** `PHA-09`

**Acceptance:**
- Run: `python -m pytest tests/unit/arch/test_constraints.py -v`
- Expected: valid capability snapshots pass; crafted illegal plans fail with named constraint ids.

### Story PHA-11: Expose planner-facing architecture query API

**Spec:** `SPEC-05`

**Goal:** Provide a narrow query surface so Phase B/C modules can ask the architecture model questions instead of reading profile internals.

**Files:**
- Create: `src/llm_sched/arch/query_api.py`
- Create: `tests/unit/arch/test_query_api.py`

**Deliverables:**
- Queries such as `supports_mode()`, `vmem_region()`, `opcode_enabled()`, `shared_dma_bandwidth()`, `kv_layout_rule()`, and `link_available()`.
- Return shapes stable enough for tiling, scheduling, and descriptor modules.

**Depends On:** `PHA-09`, `PHA-10`

**Acceptance:**
- Run: `python -m pytest tests/unit/arch/test_query_api.py -v`
- Expected: query API returns deterministic answers for both baseline profiles.

### Story PHA-12: Define IR schemas and versioned validators

**Spec:** `SPEC-06`

**Goal:** Freeze the field-level structure and invariants of `Graph IR`, `NIG`, `Schedule IR`, `Descriptor IR`, and `Analysis IR`.

**Files:**
- Create: `src/llm_sched/ir/graph_ir.py`
- Create: `src/llm_sched/ir/nig.py`
- Create: `src/llm_sched/ir/schedule_ir.py`
- Create: `src/llm_sched/ir/descriptor_ir.py`
- Create: `src/llm_sched/ir/analysis_ir.py`
- Create: `src/llm_sched/ir/validators.py`
- Create: `tests/unit/ir/test_ir_validators.py`

**Deliverables:**
- Typed models for each IR layer.
- Version field per IR document.
- Validators for required fields and mode-specific invariants.

**Depends On:** `PHA-01`, `PHA-09`

**Acceptance:**
- Run: `python -m pytest tests/unit/ir/test_ir_validators.py -v`
- Expected: valid minimal IR documents pass; invalid `single-core` / `dual-core` edge cases fail.

### Story PHA-13: Add IR traceability and audit reference contract

**Spec:** `SPEC-06`

**Goal:** Guarantee that later lowering and reporting layers can trace any object back to its upstream source.

**Files:**
- Modify: `src/llm_sched/ir/graph_ir.py`
- Modify: `src/llm_sched/ir/nig.py`
- Modify: `src/llm_sched/ir/schedule_ir.py`
- Modify: `src/llm_sched/ir/descriptor_ir.py`
- Create: `tests/unit/ir/test_ir_traceability.py`

**Deliverables:**
- Stable ids and `audit_ref`/`source_ref` fields.
- Rules for how ids are preserved or remapped across layers.
- Contract docstring explaining allowed one-to-many and many-to-one mappings.

**Depends On:** `PHA-12`

**Acceptance:**
- Run: `python -m pytest tests/unit/ir/test_ir_traceability.py -v`
- Expected: a descriptor object can point back to schedule and upstream semantic ids without ambiguity.

### Story PHA-14: Add IR serialization, dump, and reload contract

**Spec:** `SPEC-06`

**Goal:** Make every IR layer storable, diffable, and reloadable as a first-class artifact.

**Files:**
- Create: `src/llm_sched/ir/io.py`
- Create: `tests/unit/ir/test_ir_roundtrip.py`

**Deliverables:**
- JSON serialization helpers for all IR types.
- Round-trip load/save support.
- Stable dump file naming convention aligned with run manifest contract.

**Depends On:** `PHA-12`, `PHA-13`, `PHA-06`

**Acceptance:**
- Run: `python -m pytest tests/unit/ir/test_ir_roundtrip.py -v`
- Expected: all IR layers round-trip through JSON without losing schema version or ids.

### Story PHA-15: Build invariant regression suite for all IR layers

**Spec:** `SPEC-06`

**Goal:** Turn the IR contract into a guarded interface, not a doc-only promise.

**Files:**
- Create: `tests/unit/ir/test_graph_ir_invariants.py`
- Create: `tests/unit/ir/test_nig_invariants.py`
- Create: `tests/unit/ir/test_schedule_ir_invariants.py`
- Create: `tests/unit/ir/test_descriptor_ir_invariants.py`
- Create: `tests/unit/ir/test_analysis_ir_invariants.py`

**Deliverables:**
- Per-layer invariant tests.
- Regression fixtures for valid and invalid examples.
- One aggregated test target for CI.

**Depends On:** `PHA-12`, `PHA-14`

**Acceptance:**
- Run: `python -m pytest tests/unit/ir -v`
- Expected: validators cover all five IR layers and fail with explicit messages on invariant breaks.

### Story PHA-16: Publish Phase A smoke flow and handoff docs

**Spec:** `SPEC-01`, `SPEC-02`, `SPEC-05`, `SPEC-06`

**Goal:** Produce the minimum docs that let another engineer run the foundation stack and understand what is ready for Phase B.

**Files:**
- Create: `docs/development/phase-a-foundation-handoff.md`
- Modify: `docs/development/README.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`

**Deliverables:**
- One handoff doc describing what commands work in Phase A.
- One checklist of what later phases can assume is stable.
- A short gap list of what remains intentionally unimplemented.

**Depends On:** `PHA-05`, `PHA-08`, `PHA-11`, `PHA-15`

**Acceptance:**
- Handoff doc includes:
  - supported commands,
  - checked-in profiles,
  - architecture query examples,
  - IR dump examples,
  - explicit non-goals for Phase A.

## Execution Order

Run the stories in this order:

1. `PHA-01`
2. `PHA-02`, `PHA-03`
3. `PHA-04`
4. `PHA-05`, `PHA-06`
5. `PHA-07`
6. `PHA-08`, `PHA-09`
7. `PHA-10`, `PHA-12`
8. `PHA-11`, `PHA-13`
9. `PHA-14`
10. `PHA-15`
11. `PHA-16`

## Definition of Done for Phase A

Phase A is done only when all of the following are true:

- Target and scenario profiles are versioned, validated, and load through one public API.
- A CLI can validate profiles and create a run root with a manifest.
- Architecture capabilities and hard constraints are queryable without reading raw JSON.
- All five IR layers have typed schemas, validators, and JSON round-trip support.
- Regression tests guard the profile contracts, architecture model, and IR invariants.
- The project has a handoff doc that clearly defines what later phases may rely on.
