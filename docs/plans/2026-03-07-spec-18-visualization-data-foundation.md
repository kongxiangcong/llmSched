# SPEC-18 Visualization Data Foundation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the first stable visualization-facing data bundle that packages one run-root into UI-consumable graph/timeline/KV/VMEM/coverage views, with optional sweep context.

**Architecture:** Introduce a static `VisualizationBundle` contract instead of a live query service. A packaging workflow will read existing run-root artifacts and reports, normalize them into stable view models, optionally attach filtered sweep deltas from a sweep workspace, and emit one `visualization_bundle.json` artifact that isolates UI consumers from internal IR/report schema changes.

**Tech Stack:** Python 3.14, Pydantic models, existing run-root pipeline/CLI pattern, pytest unit/smoke tests.

---

### Task 1: Add Visualization Bundle Contract

**Files:**
- Create: `src/llm_sched/contracts/visualization_bundle.py`
- Modify: `src/llm_sched/contracts/__init__.py`
- Create: `tests/unit/contracts/test_visualization_bundle.py`

**Step 1: Write the failing test**

Add contract tests covering:
- `VisualizationBundle`
- `VisualizationViewIndex`
- graph/timeline/KV/VMEM/coverage view models
- optional sweep view model
- run summary metadata and issue list

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/contracts/test_visualization_bundle.py -q`
Expected: FAIL because the contract file does not exist.

**Step 3: Write minimal implementation**

Create summary-grade models for:
- run metadata
- graph nodes and edges
- timeline blocks
- KV summary/formulas
- VMEM regions/diagnostics
- coverage summary
- optional sweep summary
- top-level `VisualizationBundle`

Do not add HTTP handlers or frontend-specific rendering fields.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/contracts/test_visualization_bundle.py -q`
Expected: PASS

### Task 2: Add Visualization Bundle Builder

**Files:**
- Create: `src/llm_sched/analysis/visualization_bundle_builder.py`
- Modify: `src/llm_sched/analysis/__init__.py`
- Create: `tests/unit/analysis/test_visualization_bundle_builder.py`

**Step 1: Write the failing tests**

Add builder tests for:
- prefill run -> graph/timeline/KV/VMEM/coverage views
- decode run -> decode-aware KV view
- optional sweep report -> filtered sweep section
- missing sweep context -> no crash and `sweep_view = None`

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/analysis/test_visualization_bundle_builder.py -q`
Expected: FAIL because the builder does not exist.

**Step 3: Write minimal implementation**

Implement:
- `build_visualization_bundle(...)`

Input should be loaded typed models, not raw JSON strings. Keep the bundle view-model grade:
- UI should not need to understand Graph IR, Schedule IR, or MemoryPlan internals
- graph view should normalize nodes/edges and op counts
- timeline should normalize schedule blocks
- KV/VMEM/coverage should summarize existing contracts
- sweep should remain optional and filtered to the current scenario/target context

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/analysis/test_visualization_bundle_builder.py -q`
Expected: PASS

### Task 3: Add Visualization Packaging Workflow

**Files:**
- Create: `src/llm_sched/pipeline/visualization_packaging.py`
- Modify: `src/llm_sched/pipeline/__init__.py`
- Create: `tests/unit/pipeline/test_visualization_packaging_workflow.py`

**Step 1: Write the failing tests**

Add workflow tests verifying:
- packaging one completed run-root writes `reports/visualization_bundle.json`
- optional `sweep_root` attaches sweep context when `reports/sweep_delta_report.json` exists
- manifest artifact index is updated
- invalid run-roots fail cleanly without traceback-grade errors

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/pipeline/test_visualization_packaging_workflow.py -q`
Expected: FAIL because the workflow does not exist.

**Step 3: Write minimal implementation**

Implement:
- `run_visualization_packaging(run_root, sweep_root=None)`

Workflow responsibilities:
- load manifest and required artifacts
- resolve single-core vs dual-core schedule path
- load prefill or decode report based on scenario
- optionally load one sweep report from `sweep_root`
- emit `reports/visualization_bundle.json`
- write manifest/run-summary updates

Do not add live serving, caching, or multi-run catalog logic in this batch.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/pipeline/test_visualization_packaging_workflow.py -q`
Expected: PASS

### Task 4: Add CLI And Smoke Gates

**Files:**
- Modify: `src/llm_sched/cli/main.py`
- Create: `tests/smoke/test_cli_run_visualization_packaging.py`
- Create: `tests/smoke/test_phase_e_visualization_foundation_matrix.py`

**Step 1: Write the failing tests**

Add smoke tests for:
- `llm-sched run-visualization-packaging --run-root ...`
- `llm-sched run-visualization-packaging --run-root ... --sweep-root ...`
- Gemma3 `single-core/dual-core x prefill/decode` visualization packaging matrix
- missing report path failing without traceback

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/smoke/test_cli_run_visualization_packaging.py tests/smoke/test_phase_e_visualization_foundation_matrix.py -q`
Expected: FAIL because the CLI command does not exist.

**Step 3: Write minimal implementation**

Add CLI wiring and user-facing messages only. Do not add a web server or UI assets in this batch.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/smoke/test_cli_run_visualization_packaging.py tests/smoke/test_phase_e_visualization_foundation_matrix.py -q`
Expected: PASS

### Task 5: Docs, Verification, Commit

**Files:**
- Create: `docs/development/phase-e-visualization-foundation-handoff.md`
- Modify: `docs/development/README.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`

**Step 1: Update docs**

Document:
- stable `VisualizationBundle` assumptions
- workflow and CLI entrypoint
- what `SPEC-19` may now assume

**Step 2: Run focused verification**

Run:
- `python -m pytest tests/unit/contracts/test_visualization_bundle.py tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/pipeline/test_visualization_packaging_workflow.py tests/smoke/test_cli_run_visualization_packaging.py tests/smoke/test_phase_e_visualization_foundation_matrix.py -q`

Expected: PASS

**Step 3: Run full verification**

Run:
- `python -m pytest -q`
- `git diff --check`

Expected: PASS with no diff errors.

**Step 4: Commit**

```bash
git add src/llm_sched/contracts/visualization_bundle.py src/llm_sched/contracts/__init__.py src/llm_sched/analysis/visualization_bundle_builder.py src/llm_sched/analysis/__init__.py src/llm_sched/pipeline/visualization_packaging.py src/llm_sched/pipeline/__init__.py src/llm_sched/cli/main.py docs/development/README.md docs/development/evaluation-compiler-roadmap.md docs/development/phase-e-visualization-foundation-handoff.md docs/plans/2026-03-07-spec-18-visualization-data-foundation.md tests/unit/contracts/test_visualization_bundle.py tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/pipeline/test_visualization_packaging_workflow.py tests/smoke/test_cli_run_visualization_packaging.py tests/smoke/test_phase_e_visualization_foundation_matrix.py
git commit -m "feat: add spec 18 visualization data foundation"
```
