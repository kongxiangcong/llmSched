# Codebase Concerns

**Analysis Date:** 2026-04-21

## Tech Debt

**Duplicated Pipeline Helpers:**
- Issue: `_write_manifest`, `_write_run_summary`, and `_relative_to_run` are copy-pasted into 15+ pipeline workflow files.
- Files: `src/llm_sched/pipeline/frontend_analysis.py`, `src/llm_sched/pipeline/memory_planning.py`, `src/llm_sched/pipeline/tile_planning.py`, `src/llm_sched/pipeline/single_core_scheduling.py`, `src/llm_sched/pipeline/dual_core_scheduling.py`, `src/llm_sched/pipeline/descriptor_generation.py`, `src/llm_sched/pipeline/performance_estimation.py`, `src/llm_sched/pipeline/prefill_evaluation.py`, `src/llm_sched/pipeline/decode_evaluation.py`, `src/llm_sched/pipeline/visualization_packaging.py`, `src/llm_sched/pipeline/diagnosis_analysis.py`, `src/llm_sched/pipeline/diagnosis_workbench.py`, `src/llm_sched/pipeline/diagnosis_packaging.py`, `src/llm_sched/pipeline/visualization_workbench.py`, `src/llm_sched/pipeline/visualization_catalog.py`, `src/llm_sched/pipeline/memory_planner_closure.py`, `src/llm_sched/pipeline/phase_c_acceptance.py`, `src/llm_sched/pipeline/phase_d_compare.py`
- Impact: Any change to manifest/summary serialization requires editing 15+ files. Risk of divergence.
- Fix approach: Extract helpers into `src/llm_sched/pipeline/_common.py` or similar shared module.

**Dead Code in `diagnosis_analysis.py`:**
- Issue: Two sets of builder functions exist -- an older set taking `(run_root, manifest, artifact_index)` and a newer set taking `ctx`. Only the `ctx`-based versions are called from `run_diagnosis_analysis`.
- Files: `src/llm_sched/pipeline/diagnosis_analysis.py` lines 406-688 (unused), lines 691+ (active)
- Impact: 280+ lines of unreachable code in a 944-line file, increasing maintenance burden.
- Fix approach: Remove the unused `(run_root, manifest, artifact_index)` builder functions.

**Duplicated Magic Constants:**
- Issue: `_DEFAULT_K_TILE_SIZE = 128` is defined in both `binding.py` and `legality.py`.
- Files: `src/llm_sched/frontend/binding.py:15`, `src/llm_sched/frontend/legality.py:22`
- Impact: Risk of inconsistent tile size defaults if one is changed without the other.
- Fix approach: Move to a shared `frontend/constants.py` module.

**Embedded JavaScript in Python:**
- Issue: `catalog_builder.py` and `workbench_builder.py` embed thousands of lines of HTML/CSS/JS as Python f-strings.
- Files: `src/llm_sched/visualization/catalog_builder.py` (3123 lines), `src/llm_sched/visualization/workbench_builder.py` (2572 lines)
- Impact: No IDE support, no JS linting, no syntax highlighting, hard to test, large file sizes.
- Fix approach: Extract JS/CSS into template files under `src/llm_sched/visualization/templates/` and render with `jinja2` or simple file reads.

**No Logging Framework:**
- Issue: The entire `src/llm_sched/` tree contains zero `import logging` statements. There are also zero `print()` statements.
- Impact: Silent failures in production. The only observability is the `RunSummary` diagnostics list, which is only written on failure.
- Fix approach: Add structured logging (Python `logging` module) at `INFO`/`WARNING`/`ERROR` levels in all pipeline stages.

**Broad Exception Handling:**
- Issue: Every pipeline workflow catches `except Exception` as the top-level error boundary.
- Files: All 19 pipeline files in `src/llm_sched/pipeline/`
- Impact: KeyboardInterrupt, SystemExit, and unexpected bugs are swallowed. Stack traces are lost because only `str(exc)` is preserved.
- Fix approach: Catch specific expected exceptions (FileNotFoundError, ValidationError) and let unexpected exceptions propagate with full tracebacks.

## Known Bugs

**Unused `os` imports:**
- Issue: `import os` exists in three visualization pipeline files but is never referenced.
- Files: `src/llm_sched/pipeline/diagnosis_workbench.py:6`, `src/llm_sched/pipeline/visualization_workbench.py:6`, `src/llm_sched/pipeline/visualization_catalog.py:6`
- Trigger: Static analysis flags.
- Workaround: None needed, but indicates lack of lint enforcement.

## Security Considerations

**Subprocess Execution Without Validation:**
- Issue: `end_to_end_runner.py` calls `subprocess.run` with dynamically constructed CLI arguments.
- Files: `src/llm_sched/tools/end_to_end_runner.py:842`
- Risk: If any path or argument is user-controlled, command injection is possible.
- Current mitigation: Arguments are built from internal `RunCase` dataclasses, not raw user input.
- Recommendations: Validate all path components with `Path.resolve()` and avoid shell=True.

**JSON Deserialization Without Schema Versioning:**
- Issue: `load_ir_document` uses `json.loads` + `model_type.model_validate` but IR documents have no version field.
- Files: `src/llm_sched/ir/io.py:24-27`
- Risk: Loading an old IR dump with a newer model class can produce silent data corruption or confusing validation errors.
- Current mitigation: Pydantic validation catches type mismatches.
- Recommendations: Add a `schema_version` field to all IR base classes and reject incompatible versions.

## Performance Bottlenecks

**Large File I/O in Diagnosis Context:**
- Issue: `build_diagnosis_context` eagerly loads every artifact into memory (GraphIR, NIGIR, MemoryPlan, ScheduleIR, DescriptorIR, multiple reports).
- Files: `src/llm_sched/analysis/diagnosis_context.py:112-199`
- Cause: No lazy loading -- all JSON files are parsed even if only one report is needed.
- Improvement path: Add lazy properties or accept a `required_reports` parameter to skip unnecessary loads.

**Visualization Builders Generate Large Strings:**
- Issue: `catalog_builder.py` and `workbench_builder.py` build multi-thousand-line HTML/JS strings in memory.
- Files: `src/llm_sched/visualization/catalog_builder.py`, `src/llm_sched/visualization/workbench_builder.py`
- Cause: Entire catalogs are rendered as single strings before writing.
- Improvement path: Stream-write to files or use a template engine with file-based templates.

**Repeated `model_dump(mode="json")` Calls:**
- Issue: 55 calls to `model_dump(mode="json")` across the codebase, many in hot paths.
- Files: Pipeline files, report builders, IR I/O
- Cause: No centralized serialization helper for pydantic objects.
- Improvement path: Use `dump_ir_document` consistently or add a `to_json_file` method on base contract classes.

## Fragile Areas

**Diagnosis Analysis (944 lines):**
- Files: `src/llm_sched/pipeline/diagnosis_analysis.py`
- Why fragile: Contains 17 `assert ... is not None` statements, dead code, and a complex chain of nullable report dependencies. A single missing artifact causes cascading `None` returns.
- Safe modification: Always run the full smoke test suite after changes. The `tests/smoke/` conftest has session-scoped fixtures that cache prepared run roots.
- Test coverage: Unit tests exist but the integration surface is large.

**Descriptor Estimator (1672 lines):**
- Files: `src/llm_sched/analysis/descriptor_estimator.py`
- Why fragile: Heavy use of `defaultdict`, `Counter`, and deeply nested tuple return types. Multiple functions return `None` or empty dicts on missing inputs, making call chains hard to trace.
- Safe modification: Add type stubs for the nested return types. Extract smaller pure functions.
- Test coverage: No dedicated unit test file found for descriptor_estimator.

**Canonicalization (2113 lines):**
- Files: `src/llm_sched/frontend/canonicalize.py`
- Why fragile: Single `# type: ignore[assignment]` in the entire codebase at line 1032. Complex graph mutation with many fusion passes.
- Safe modification: Add unit tests for each fusion pass in isolation.
- Test coverage: `tests/unit/frontend/test_canonicalize.py` exists (1430 lines).

**Dual-Core Scheduler:**
- Files: `src/llm_sched/planning/dual_core_scheduler.py`
- Why fragile: Imports private functions from `single_core_scheduler.py` (`_buffer_binding`, `_group_allocations_by_node`, `_select_candidate`, etc.).
- Files: `src/llm_sched/planning/dual_core_scheduler.py:26-34`
- Safe modification: Promote shared helpers to a public module or merge into a shared `scheduling_common.py`.
- Test coverage: `tests/unit/planning/test_dual_core_scheduler.py` (2041 lines).

**Sweep Analysis:**
- Files: `src/llm_sched/pipeline/sweep_analysis.py`
- Why fragile: Catches `except Exception` at two levels (spec parsing and full sweep). Nested try blocks with broad catches.
- Safe modification: Separate spec validation from execution. Add per-run error collection instead of failing the entire sweep.

## Scaling Limits

**Contract Class Proliferation:**
- Current capacity: 35 contract files, 28 Report/Artifact classes, 452 pydantic references.
- Limit: As the pipeline grows, contract cross-dependencies become a dense graph. Adding a field requires updating multiple builders.
- Scaling path: Consider code generation from a schema definition or stricter versioning.

**Test Suite Size:**
- Current capacity: 536 test functions, 46,596 lines of test code.
- Limit: Smoke tests rely on session-scoped caching in `tests/smoke/conftest.py` and `tests/unit/pipeline/conftest.py`. Cache invalidation is manual.
- Scaling path: Add cache versioning or switch to deterministic fixture factories.

## Dependencies at Risk

**Pydantic v2:**
- Risk: Heavy reliance on `model_validate_json`, `model_dump(mode="json")`, `ConfigDict(extra="forbid")`. A major pydantic v3 release would require widespread changes.
- Impact: 452+ references across contracts and pipeline.
- Migration plan: Pin to `pydantic>=2.12,<3` in `pyproject.toml` and monitor release notes.

**Typer:**
- Risk: CLI built entirely on typer. Breaking changes in typer 1.x could affect `src/llm_sched/cli/main.py`.
- Impact: All 19 pipeline commands exposed through CLI.
- Migration plan: Pin to `typer>=0.24,<1` or add CLI abstraction layer.

## Missing Critical Features

**No Schema Versioning for IR or Reports:**
- Problem: IR dumps and report JSON have no `schema_version` field.
- Blocks: Safe backward compatibility when evolving contracts.

**No Structured Logging:**
- Problem: Zero logging infrastructure.
- Blocks: Production observability, debugging failed runs at scale.

**No Lint/Format Enforcement:**
- Problem: No `.pre-commit-config.yaml`, no `ruff`, `black`, or `mypy` configuration detected.
- Blocks: Consistent code quality. Dead imports and type errors slip through.

## Test Coverage Gaps

**Descriptor Estimator:**
- What's not tested: `src/llm_sched/analysis/descriptor_estimator.py` (1672 lines) has no dedicated unit test file.
- Files: `src/llm_sched/analysis/descriptor_estimator.py`
- Risk: Performance estimation bugs could go unnoticed until integration smoke tests.
- Priority: High

**Visualization Builders:**
- What's not tested: `catalog_builder.py` and `workbench_builder.py` generate HTML/JS but output is only validated through smoke tests.
- Files: `src/llm_sched/visualization/catalog_builder.py`, `src/llm_sched/visualization/workbench_builder.py`
- Risk: JavaScript syntax errors or broken HTML structure only caught by manual inspection.
- Priority: Medium

**End-to-End Runner:**
- What's not tested: `src/llm_sched/tools/end_to_end_runner.py` (1006 lines) orchestrates subprocess calls but has no direct unit tests.
- Files: `src/llm_sched/tools/end_to_end_runner.py`
- Risk: CLI argument construction bugs only caught by full smoke runs.
- Priority: Medium

---

*Concerns audit: 2026-04-21*
