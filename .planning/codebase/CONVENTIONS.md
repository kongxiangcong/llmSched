# Coding Conventions

**Analysis Date:** 2026-04-21

## Naming Patterns

**Files:**
- Modules use `snake_case.py`: `single_core_scheduler.py`, `frontend_analysis.py`
- Test files use `test_{module_name}.py`: `test_single_core_scheduler.py`, `test_frontend_analysis_workflow.py`
- Pipeline modules named after workflow stages: `dual_core_scheduling.py`, `memory_planning.py`

**Functions:**
- Public functions use `snake_case`: `plan_single_core_schedule`, `run_frontend_analysis`
- Private helpers use leading underscore: `_build_pending_blocks`, `_write_manifest`, `_safe_ratio`
- Test functions use descriptive `snake_case` prefixed with `test_`: `test_plan_single_core_schedule_emits_ordered_blocks_for_quant_gemm`
- Factory fixtures use `*_factory` suffix: `prepared_run_root_factory`, `minimal_descriptor_run_root_factory`

**Variables:**
- Local variables use `snake_case`: `issue_slot`, `block_end_slots`, `ready_heap`
- Type hints use PascalCase: `NIGIR`, `ScheduleIR`, `TileCandidate`
- Constants use `UPPER_SNAKE_CASE`: `EXIT_OK`, `EXIT_VALIDATION_ERROR`, `SMOKE_STAGES`
- Module-level private constants use leading underscore: `_GEMM_COMPUTE_RESOURCES`, `_STAGE_POLICIES`

**Types:**
- Pydantic models use `PascalCase`: `RunManifest`, `ScheduleBlock`, `Diagnostic`
- Dataclasses use `PascalCase` with frozen/slots when appropriate: `_PendingBlock`
- Type aliases use `PascalCase`: `TensorMemoryClass = Literal[...]`
- Enums and literals use descriptive string values: `"single-core"`, `"dual-core"`, `"prefill"`, `"decode"`

**Classes:**
- Pydantic `BaseModel` subclasses for all schema objects: `RunManifest`, `NIGNode`, `ScheduleIR`
- `ConfigDict(extra="forbid")` enforced on nearly all models to prevent accidental field drift
- Custom exceptions inherit from a base project exception: `ProfileLoadError` -> `MalformedProfileError`, `ProfileValidationFailure`

## Code Style

**Formatting:**
- No explicit formatter config detected (no `.prettierrc`, `ruff.toml`, or `biome.json`)
- Python 3.11+ syntax used throughout (union types with `|`, `match` not yet observed)
- `from __future__ import annotations` present in most modules for forward reference compatibility
- Indentation: 4 spaces
- Line length appears to follow ~100-120 character soft limit

**Linting:**
- No explicit linter config detected
- Type hints are pervasive; function signatures include return types
- `typing.Any` used sparingly for attribute dicts and ONNX proto handling

## Import Organization

**Order:**
1. `from __future__ import annotations` (when used)
2. Standard library: `json`, `pathlib`, `collections`, `typing`
3. Third-party: `pydantic`, `onnx`, `typer`, `pytest`
4. Project internal: `llm_sched.*`
5. Test-only imports: `from tests_diagnosis_baseline import ...`

**Path Aliases:**
- No path aliases configured; all imports are absolute from `llm_sched`
- Tests add `src/` to `sys.path` via `tests/conftest.py` to enable `from llm_sched import ...`

**Barrel Files:**
- `llm_sched/pipeline/__init__.py` re-exports all workflow functions and result types
- `llm_sched/frontend/__init__.py` re-exports frontend entrypoints
- Subpackage `__init__.py` files exist but are not all heavily used as barrels

## Error Handling

**Patterns:**
- Pipeline workflows wrap the entire body in `try/except Exception` and emit structured `RunSummary` with diagnostics
- `Diagnostic` Pydantic model carries `path`, `field`, `severity`, `message` for uniform error reporting
- Custom exceptions carry `diagnostics: list[Diagnostic]` for batch validation errors
- CLI commands check `result.status != "completed"` and surface the first diagnostic message
- `ValueError` used for precondition failures in scheduler/planner logic with explicit mismatch descriptions

**Example from `src/llm_sched/pipeline/dual_core_scheduling.py`:**
```python
try:
    manifest = RunManifest.model_validate_json(...)
    # ... workflow ...
except Exception as exc:
    diagnostics = [Diagnostic(...)]
    _write_run_summary(..., RunSummary(status="failed", exit_code=1, diagnostics=diagnostics))
    return DualCoreSchedulingResult(status="failed", diagnostics=diagnostics)
```

## Logging

**Framework:** No dedicated logging framework detected; uses `typer.echo` in CLI for user-facing output.

**Patterns:**
- CLI commands echo success/failure messages via `typer.echo`
- Pipeline stages write machine-readable `RunSummary` JSON instead of log files
- No `logging.getLogger` usage observed

## Comments

**When to Comment:**
- Module docstrings describe the SPEC number: `"SPEC-10 deterministic single-core scheduler foundation"`
- Function docstrings are minimal; behavior is expressed through descriptive names
- Inline comments are rare; complex scheduling logic is self-describing via variable names

**JSDoc/TSDoc:**
- Not applicable (Python project)
- Pydantic model fields use `Field(description=...)` sparingly; validation constraints via `Field(gt=0)`

## Function Design

**Size:**
- Pipeline `run_*` functions are large (100-200 lines) and follow a consistent template: load manifest, load artifacts, execute, write artifacts, update manifest, write summary
- Scheduler/planner functions are medium (50-100 lines) with extracted private helpers
- Test functions are focused, typically 10-40 lines each

**Parameters:**
- Prefer keyword-only arguments for optional/configurable parameters using `*,`
- Pydantic models passed as typed arguments rather than raw dicts
- `Path` objects preferred over strings for filesystem paths

**Return Values:**
- Pipeline functions return a `*Result` Pydantic model with `status`, paths, and `diagnostics`
- Pure functions return domain objects: `ScheduleIR`, `MemoryPlanArtifact`
- Boolean success/failure is never returned; always use structured result or raise

## Module Design

**Exports:**
- `__all__` defined in major package `__init__.py` files (`pipeline`, `frontend`)
- Private helpers kept module-local with leading underscore

**Barrel Files:**
- `llm_sched/pipeline/__init__.py` is the primary workflow entrypoint barrel
- `llm_sched/frontend/__init__.py` is the primary frontend barrel
- IR subpackages (`ir/graph_ir.py`, `ir/nig.py`) are imported directly, not barrel-exported

## JSON Serialization

**Pattern:**
- All Pydantic models serialize with `model_dump(mode="json")`
- Files written with `indent=2` and `encoding="utf-8"`
- Round-trip validated via `model_validate_json` or `model_validate`
- IR documents use `dump_ir_document` / `load_ir_document` helpers in `src/llm_sched/ir/io.py`

## Type Safety

**Patterns:**
- `Literal` types for enumerated string fields: `Literal["initialized", "failed", "completed"]`
- `ConfigDict(extra="forbid")` prevents accidental schema drift
- `model_validator(mode="after")` used for cross-field validation (e.g., NIGIR node uniqueness)
- `isinstance` checks used in pipeline builders before casting generic `object` parameters

---

*Convention analysis: 2026-04-21*
