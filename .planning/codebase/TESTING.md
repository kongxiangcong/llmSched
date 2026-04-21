# Testing Patterns

**Analysis Date:** 2026-04-21

## Test Framework

**Runner:**
- pytest >=9,<10
- Config: `pyproject.toml` (`[tool.pytest.ini_options]`)
- Testpaths: `["tests"]`
- Custom markers:
  - `local_smoke`: representative smoke subset for local iteration
  - `milestone_matrix`: broader matrix smoke for milestone and nightly closure

**Assertion Library:**
- Built-in `assert` (pytest style)
- `pytest.approx` for float comparisons
- `pytest.raises` for exception testing
- `pytest.mark.parametrize` for matrix-style test expansion

**Run Commands:**
```bash
pytest                              # Run all tests
pytest -m local_smoke               # Run local smoke subset
pytest -m milestone_matrix          # Run milestone matrix subset
pytest --co -q                      # Collect and list tests without running
```

## Test File Organization

**Location:**
- Tests are co-located under `tests/` mirroring source structure:
  - `tests/unit/planning/` -> `src/llm_sched/planning/`
  - `tests/unit/pipeline/` -> `src/llm_sched/pipeline/`
  - `tests/unit/contracts/` -> `src/llm_sched/contracts/`
  - `tests/smoke/` -> CLI end-to-end smoke tests

**Naming:**
- Unit tests: `test_{module_name}.py`
- Smoke tests: `test_cli_run_{command}.py`, `test_phase_{letter}_{feature}_matrix.py`

**Structure:**
```
tests/
├── conftest.py                     # Root: adds src/ to sys.path
├── smoke/
│   ├── conftest.py                 # Smoke fixtures: CLI runner, prepared run roots
│   ├── test_cli_help.py
│   ├── test_cli_init_run.py
│   └── test_phase_c_descriptor_matrix.py
├── unit/
│   ├── analysis/
│   ├── arch/
│   ├── config/
│   ├── contracts/
│   ├── frontend/
│   ├── ir/
│   ├── pipeline/
│   │   └── conftest.py             # Pipeline fixtures: minimal run roots
│   ├── planning/
│   ├── tools/
│   └── visualization/
```

## Test Structure

**Suite Organization:**
- No class-based test suites; all tests are module-level functions
- Each test function is self-contained with inline fixture/builder calls

**Patterns:**
```python
def test_plan_single_core_schedule_emits_ordered_blocks_for_quant_gemm() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.memory_planner import plan_memory_artifact
    from llm_sched.planning.single_core_scheduler import plan_single_core_schedule
    from llm_sched.planning.tile_planner import plan_tiling_artifact

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "prefill_seq128.json")
    bound_nig = _make_bound_nig_ir([...])
    memory_plan = plan_memory_artifact(bound_nig, target, scenario)
    tiling_plan = plan_tiling_artifact(bound_nig, memory_plan, target, scenario)

    schedule = plan_single_core_schedule(bound_nig, memory_plan, tiling_plan, target, scenario)

    stages = [block.stage for block in schedule.blocks if block.node_id == "nig.node.linear"]
    assert stages == ["dma_in", "compute", "store"]
```

**Setup/Teardown:**
- Heavy setup delegated to session-scoped fixtures in `conftest.py`
- `tmp_path` / `tmp_path_factory` used for filesystem isolation
- `prepared_run_root_factory` caches prepared run roots across session to avoid re-running CLI stages

## Mocking

**Framework:** pytest built-ins (`monkeypatch`) and `unittest.mock.patch`

**Patterns:**
- `monkeypatch.setattr` for replacing internal functions in end-to-end runner tests:
```python
monkeypatch.setattr("llm_sched.tools.end_to_end_runner._execute_run_case", fake_execute_run_case)
```
- `unittest.mock.patch` for context-manager style mocking in pipeline workflow tests:
```python
from unittest.mock import patch

with patch("llm_sched.pipeline.performance_estimation._load_schedule_ir") as mock_load:
    ...
```

**What to Mock:**
- CLI subprocess calls in unit tests (replace with fake functions)
- Internal loaders when testing error paths in pipeline workflows
- File system boundaries when testing catalog/visualization packaging

**What NOT to Mock:**
- Core scheduler/planner algorithms tested against real data
- IR validators tested with real JSON payloads
- Contract builders tested with real Pydantic model instances

## Fixtures and Factories

**Test Data:**
- Inline fixture builders in test modules: `_make_bound_nig_ir`, `_make_wdq_gemm_node`, `_make_sdpa_node`
- `conftest.py` factories return closures for parameterized run root preparation:
```python
@pytest.fixture(scope="session")
def prepared_run_root_factory(tmp_path_factory: pytest.TempPathFactory, repo_root: Path):
    cache_root = tmp_path_factory.mktemp("prepared-run-roots", numbered=False)
    def factory(*, target_run_root: Path, target_relative_path: str, scenario_relative_path: str, final_stage: str) -> Path:
        ...
    return factory
```

**Location:**
- Root `tests/conftest.py`: path manipulation only
- `tests/smoke/conftest.py`: CLI runner, sweep factories, diagnosis baseline loaders
- `tests/unit/pipeline/conftest.py`: minimal run root factories for pipeline unit tests

## Coverage

**Requirements:** No explicit coverage target configured.

**View Coverage:**
```bash
pytest --cov=llm_sched --cov-report=term-missing
```
(Requires `pytest-cov` to be installed separately.)

## Test Types

**Unit Tests:**
- Scope: individual functions, contract builders, IR validators
- Approach: construct minimal inputs inline, assert on outputs
- No external process spawning; pure Python execution
- Example: `tests/unit/planning/test_single_core_scheduler.py` (29 test functions)

**Integration Tests:**
- Scope: pipeline workflows that read/write artifacts to `tmp_path`
- Approach: initialize a run root, invoke `run_*` function, assert on emitted files
- Example: `tests/unit/pipeline/test_frontend_analysis_workflow.py`

**Smoke Tests:**
- Scope: CLI commands executed via `subprocess.run` with PYTHONPATH injection
- Approach: run full CLI stage against real profiles and models
- Example: `tests/smoke/test_cli_run_single_core_scheduling.py`

**Matrix Tests:**
- Scope: parametric closure across target profiles and scenario profiles
- Approach: `pytest.mark.parametrize` or explicit matrix loops in smoke tests
- Example: `tests/smoke/test_phase_c_descriptor_matrix.py`

## Common Patterns

**Async Testing:**
- Not applicable; codebase is fully synchronous

**Error Testing:**
```python
def test_build_prefill_evaluation_report_rejects_decode_scenarios() -> None:
    from llm_sched.analysis import build_prefill_evaluation_report

    with pytest.raises(ValueError, match="prefill"):
        build_prefill_evaluation_report(...)
```

**Parametrized Testing:**
```python
@pytest.mark.parametrize(
    ("target_profile", "scenario_profile", "schedule_kind", "schedule_artifact_name"),
    [
        ("profiles/targets/riscv_npu_single_core_v1.json", "profiles/scenarios/prefill_seq128.json", "single-core", "schedule_ir"),
        ("profiles/targets/riscv_npu_dual_core_v1.json", "profiles/scenarios/decode_token1_kv2048.json", "dual-core", "dual_core_schedule_ir"),
    ],
)
def test_run_performance_estimation_writes_analysis_and_summary_artifacts(...) -> None:
    ...
```

**Round-Trip Testing:**
```python
def test_all_ir_layers_round_trip_through_json(tmp_path: Path) -> None:
    cases = [
        (graph, GraphIR, tmp_path / "graph_ir.json"),
        (nig, NIGIR, tmp_path / "nig_ir.json"),
        ...
    ]
    for document, model_type, path in cases:
        dump_ir_document(document, path)
        restored = load_ir_document(path, model_type)
        assert restored == document
```

**Fixture Caching:**
- Smoke tests use `tmp_path_factory` with `.prepared` flag files to cache expensive CLI runs across the test session
- `_smoke_cache_key` uses SHA1 of serialized parameters for deterministic cache keys

## Baseline Fixtures

**Diagnosis Baselines:**
- `tests/fixtures/diagnosis_baseline/` contains pre-generated JSON reports and CSV datasets
- Four cases: `single_core_prefill`, `dual_core_prefill`, `single_core_decode`, `dual_core_decode`
- Used by smoke tests to validate diagnosis analysis, bundling, and workbench generation without re-running full pipelines
- `tests_diagnosis_baseline.py` (at repo root) provides loader helpers consumed by `conftest.py`

---

*Testing analysis: 2026-04-21*
