# SPEC-16 Layer Diff Modes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Promote layer-delta diff modes into a shared visualization compare surface and make workbench sweep views honor the same richer layer diff semantics already emerging in catalog.

**Architecture:** Keep Phase D compare math unchanged. Add a small shared layer-diff mode taxonomy beside the existing compare-focus taxonomy, thread it through visualization bundle and catalog contracts, then reuse that metadata to persist richer layer diff state across catalog deep links, workbench rendering, and snapshot/export payloads.

**Tech Stack:** Python, Pydantic contracts, static visualization builders, generated JavaScript, pytest

---

### Task 1: Add shared layer-diff mode helpers and bundle contract surface

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\src\llm_sched\compare_grouping.py`
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\src\llm_sched\contracts\visualization_bundle.py`
- Test: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\contracts\test_visualization_bundle.py`

**Step 1: Write the failing contract test**

Add a test proving visualization compare summaries accept stable layer-diff mode metadata, including:

- allowed mode ids:
  - `top-cycle`
  - `regressions-only`
  - `top-by-bytes`
  - `top-by-fitted-work`
  - `fitted-regressions-only`
- per-mode focus compatibility (`estimated-layer` or `fitted-layer`)
- a compact summary label for the mode

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/contracts/test_visualization_bundle.py -q
```

Expected: FAIL because compare summaries do not yet expose layer-diff mode metadata.

**Step 3: Implement the minimal shared surface**

Add:

- shared layer-diff mode ids/titles/default helpers in `compare_grouping.py`
- a helper that emits available layer-diff modes from existing estimated/fitted layer availability
- additive visualization bundle contract fields for available layer-diff modes

Keep this slice additive and backward compatible.

**Step 4: Run test to verify it passes**

Run:

```powershell
python -m pytest tests/unit/contracts/test_visualization_bundle.py -q
```

Expected: PASS.

### Task 2: Thread layer-diff mode metadata through visualization packaging and catalog artifacts

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\src\llm_sched\analysis\visualization_bundle_builder.py`
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\src\llm_sched\contracts\visualization_catalog.py`
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\src\llm_sched\pipeline\visualization_catalog.py`
- Test: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\analysis\test_visualization_bundle_builder.py`
- Test: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\pipeline\test_visualization_packaging_workflow.py`
- Test: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\pipeline\test_visualization_catalog_workflow.py`

**Step 1: Write the failing builder/workflow tests**

Add assertions proving:

- bundle compare summaries emit available layer-diff modes for estimated/fitted layer surfaces
- raw sweep comparisons and standalone compare reports degrade gracefully when only one layer surface exists
- catalog artifacts preserve the same layer-diff mode metadata instead of rebuilding ad-hoc UI knowledge

**Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/pipeline/test_visualization_packaging_workflow.py tests/unit/pipeline/test_visualization_catalog_workflow.py -q
```

Expected: FAIL because bundle/catalog compare summaries do not yet expose layer-diff mode metadata.

**Step 3: Implement minimal metadata wiring**

Update bundle/catalog builders to:

- build layer-diff mode metadata from existing estimated/fitted layer rows
- preserve a stable default mode per compatible focus
- avoid recomputing layer deltas outside the existing compare rows

**Step 4: Run tests to verify they pass**

Run:

```powershell
python -m pytest tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/pipeline/test_visualization_packaging_workflow.py tests/unit/pipeline/test_visualization_catalog_workflow.py -q
```

Expected: PASS.

### Task 3: Preserve layer-diff mode through catalog workspace and workbench deep links

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\src\llm_sched\visualization\catalog_builder.py`
- Test: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\visualization\test_catalog_builder.py`

**Step 1: Write the failing catalog test**

Add assertions proving generated catalog assets:

- preserve `layer_delta_focus` in workbench links and sweep drill-down links
- expose focus-aware layer-diff metadata in workspace export payloads and snapshot headers
- keep richer fitted/estimated layer-diff labels visible in generated JS

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py -q
```

Expected: FAIL because workbench deep links only preserve compare focus today and catalog exports do not surface shared layer-diff metadata.

**Step 3: Implement minimal catalog wiring**

Update catalog JS so workspace:

- keeps `layer_delta_focus` in generated workbench deep links
- carries the focused layer-diff mode into export metadata
- prefers shared compare-summary metadata over hard-coded assumptions where practical

**Step 4: Run test to verify it passes**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py -q
```

Expected: PASS.

### Task 4: Add richer layer-diff mode support to workbench sweep rendering/export

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\src\llm_sched\visualization\workbench_builder.py`
- Test: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\visualization\test_workbench_builder.py`
- Test: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\pipeline\test_visualization_workbench_workflow.py`

**Step 1: Write the failing workbench tests**

Add tests proving generated workbench assets:

- hydrate and persist `layer_delta_focus` in URL state
- filter/sort estimated and fitted layer deltas with the same richer modes used by catalog
- include the focused layer-diff mode in JSON/SVG snapshot metadata

**Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q
```

Expected: FAIL because workbench sweep state currently tracks compare focus and layer id but not richer layer-diff modes.

**Step 3: Implement minimal workbench support**

Update workbench JS to:

- persist `layer_delta_focus` in URL state and exports
- apply estimated/fitted layer-diff sorting/filtering consistently
- render focus-aware sweep summaries and focused layer metadata without introducing new compare math

**Step 4: Run tests to verify they pass**

Run:

```powershell
python -m pytest tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q
```

Expected: PASS.

### Task 5: Run focused verification and record closure

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\docs\plans\2026-03-20-spec-16-layer-diff-modes.md`

**Step 1: Run the focused verification ladder**

Run:

```powershell
python -m pytest tests/unit/contracts/test_visualization_bundle.py tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py -q
python -m pytest tests/unit/pipeline/test_visualization_packaging_workflow.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q
python -m pytest tests/smoke/test_cli_run_visualization_packaging.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q
```

Expected: PASS.

**Step 2: Record the slice outcome**

Update roadmap and plan completion notes with:

- the new shared layer-diff mode surface
- catalog/workbench adoption status
- the next remaining `SPEC-16` gap after this slice

**Step 3: Commit**

```bash
git add docs/development/evaluation-compiler-roadmap.md docs/plans/2026-03-20-spec-16-layer-diff-modes.md
git commit -m "docs: record spec16 layer diff mode closure"
```

## Completion Notes

- Completed on 2026-03-20 in `D:\workspace\llmSched\.worktrees\spec16-compare-modes`.
- Final shared layer-diff mode taxonomy:
  - `top-cycle`
  - `regressions-only`
  - `top-by-bytes`
  - `top-by-fitted-work`
  - `fitted-regressions-only`
- Implementation outcome:
  - visualization compare summaries now expose shared layer-diff mode metadata beside compare-focus metadata
  - visualization catalog artifacts preserve the same layer-diff mode payload instead of rebuilding mode knowledge locally
  - catalog workbench links now carry `layer_delta_focus` together with `compare_focus`
  - workbench sweep rendering, JSON export, and snapshot metadata now honor the focused layer-diff mode
- Verification evidence:
  - `python -m pytest tests/unit/contracts/test_visualization_bundle.py tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py -q` -> `18 passed`
  - `python -m pytest tests/unit/pipeline/test_visualization_packaging_workflow.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q` -> `13 passed`
  - `python -m pytest tests/smoke/test_cli_run_visualization_packaging.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q` -> `10 passed`
- Follow-on recommendation:
  - keep `SPEC-16` as the mainline blocker and extend compare grouping above the now-stable compare-focus plus layer-diff payload before returning to `SPEC-19`-only polish work
