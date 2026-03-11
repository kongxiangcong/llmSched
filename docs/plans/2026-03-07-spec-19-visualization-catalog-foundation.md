# SPEC-19 Visualization Catalog Foundation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the first cross-run static catalog that indexes multiple packaged workbenches and lets engineers jump across run roots from one entry page.

**Architecture:** Keep the current per-run workbench as the leaf page and add one catalog layer above it. The catalog builder will consume a list of run roots that already contain `workbench/workbench_manifest.json` and `reports/visualization_bundle.json`, then emit one static `catalog/` site with a summary table and relative links into each run's workbench.

**Tech Stack:** Python 3.14, Pydantic models, existing static visualization packaging pattern, HTML/CSS/JavaScript, pytest unit/smoke tests.

---

### Task 1: Add Catalog Contract Tests And Models

**Files:**
- Create: `src/llm_sched/contracts/visualization_catalog.py`
- Modify: `src/llm_sched/contracts/__init__.py`
- Create: `tests/unit/contracts/test_visualization_catalog.py`

**Step 1: Write the failing test**

Add contract tests covering:
- top-level catalog metadata
- per-entry run metadata and workbench link
- unique entry ids
- stable default sort key

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/contracts/test_visualization_catalog.py -q`
Expected: FAIL because the contract does not exist.

**Step 3: Write minimal implementation**

Create summary-grade models for:
- catalog metadata
- catalog entry rows
- top-level `VisualizationCatalogArtifact`

Do not add service-only fields, websocket state, or saved UI preferences.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/contracts/test_visualization_catalog.py -q`
Expected: PASS

### Task 2: Add Static Catalog Builder

**Files:**
- Create: `src/llm_sched/visualization/catalog_builder.py`
- Modify: `src/llm_sched/visualization/__init__.py`
- Create: `tests/unit/visualization/test_catalog_builder.py`

**Step 1: Write the failing test**

Add builder tests for:
- generating `catalog/index.html`, `catalog/assets/app.js`, `catalog/assets/styles.css`, `catalog/catalog_manifest.json`
- embedding relative links to per-run workbench entries
- summary table rows with scenario/mode/schedule/primary metric fields
- simple mode/schedule filtering controls

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/visualization/test_catalog_builder.py -q`
Expected: FAIL because the builder does not exist.

**Step 3: Write minimal implementation**

Implement:
- `build_visualization_catalog(entries, catalog_root)`

The builder should generate:
- one static catalog page
- one JS file for simple client-side filtering
- one CSS file for layout and table styling
- one catalog manifest JSON

Do not add a server, search backend, or run discovery in this batch.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/visualization/test_catalog_builder.py -q`
Expected: PASS

### Task 3: Add Catalog Packaging Workflow, CLI, And Smoke Gate

**Files:**
- Create: `src/llm_sched/pipeline/visualization_catalog.py`
- Modify: `src/llm_sched/pipeline/__init__.py`
- Modify: `src/llm_sched/cli/main.py`
- Create: `tests/unit/pipeline/test_visualization_catalog_workflow.py`
- Create: `tests/smoke/test_cli_run_visualization_catalog.py`

**Step 1: Write the failing tests**

Add workflow and CLI tests verifying:
- packaging a list of run roots writes `catalog/index.html` and `catalog/catalog_manifest.json`
- workflow rejects runs missing `workbench/workbench_manifest.json`
- CLI accepts repeated `--run-root`
- catalog entries point at existing relative workbench paths

**Step 2: Run tests to verify they fail**

Run:
- `python -m pytest tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q`

Expected: FAIL because the workflow and CLI do not exist.

**Step 3: Write minimal implementation**

Implement:
- `run_visualization_catalog(catalog_root, run_roots)`
- `llm-sched run-visualization-catalog --catalog-root ... --run-root ... --run-root ...`

Keep this batch explicit-list only. Do not auto-discover runs from `sweep_root`.

**Step 4: Run focused verification**

Run:
- `python -m pytest tests/unit/contracts/test_visualization_catalog.py tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q`

Expected: PASS

### Task 4: Docs, Full Verification, Commit

**Files:**
- Modify: `docs/development/phase-e-visualization-workbench-handoff.md`
- Modify: `docs/development/README.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`

**Step 1: Update docs**

Document:
- static cross-run catalog boundary
- explicit `run_root` list contract
- relationship between per-run workbench and catalog page

**Step 2: Run full verification**

Run:
- `python -m pytest -q`
- `git diff --check`

Expected: PASS with no diff errors.

**Step 3: Commit**

```bash
git add src/llm_sched/contracts/visualization_catalog.py src/llm_sched/contracts/__init__.py src/llm_sched/visualization/catalog_builder.py src/llm_sched/visualization/__init__.py src/llm_sched/pipeline/visualization_catalog.py src/llm_sched/pipeline/__init__.py src/llm_sched/cli/main.py docs/development/phase-e-visualization-workbench-handoff.md docs/development/README.md docs/development/evaluation-compiler-roadmap.md docs/plans/2026-03-07-spec-19-visualization-catalog-foundation.md tests/unit/contracts/test_visualization_catalog.py tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py
git commit -m "feat: add spec 19 visualization catalog foundation"
```
