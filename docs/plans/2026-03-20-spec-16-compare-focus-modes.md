# SPEC-16 Compare Focus Modes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add shared compare-focus modes that let downstream visualization consumers emphasize summary, pressure, schedule, estimated-layer, or fitted-layer compare views without reopening Phase D math.

**Architecture:** Keep `SPEC-16` compare math and contracts stable, then layer a thin focus-selection abstraction on top of the existing grouped scalar deltas and estimated/fitted layer deltas. Thread that focus metadata through visualization bundle building and make catalog/workbench consume the same focus helpers so links, exports, and snapshot summaries stay aligned.

**Tech Stack:** Python, Pydantic contracts, static visualization builders, generated JavaScript, pytest

---

### Task 1: Add shared compare-focus selection helpers

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\src\llm_sched\compare_grouping.py`
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\src\llm_sched\contracts\visualization_bundle.py`
- Test: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\contracts\test_visualization_bundle.py`

**Step 1: Write the failing contract test**

Add a test proving visualization compare summaries accept a stable focus-mode surface, including:

- allowed focus ids: `summary`, `memory-pressure`, `schedule-shape`, `estimated-layer`, `fitted-layer`
- a default focus id
- a compact summary label for the active focus

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/contracts/test_visualization_bundle.py -q
```

Expected: FAIL because compare-focus fields do not exist yet.

**Step 3: Add the minimal shared surface**

Implement:

- a shared compare-focus id/type in `compare_grouping.py`
- helper functions that map grouped scalar rows and layer rows onto a focus summary
- visualization bundle contract fields for available/default focus metadata

Keep this slice additive and backward compatible.

**Step 4: Run test to verify it passes**

Run:

```powershell
python -m pytest tests/unit/contracts/test_visualization_bundle.py -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add src/llm_sched/compare_grouping.py src/llm_sched/contracts/visualization_bundle.py tests/unit/contracts/test_visualization_bundle.py
git commit -m "feat: add compare focus metadata"
```

### Task 2: Build compare-focus summaries in visualization packaging

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\src\llm_sched\analysis\visualization_bundle_builder.py`
- Modify if needed: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\src\llm_sched\contracts\visualization_catalog.py`
- Test: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\analysis\test_visualization_bundle_builder.py`
- Test: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\pipeline\test_visualization_packaging_workflow.py`

**Step 1: Write the failing builder test**

Add a test proving the bundle builder emits compare-focus metadata for sweep comparisons built from:

- standalone `PhaseDCompareReport`
- raw `SweepComparison`

The test should assert that:

- summary-focused modes prefer grouped scalar summaries
- layer-focused modes prefer estimated/fitted layer deltas
- missing optional fields degrade gracefully

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/pipeline/test_visualization_packaging_workflow.py -q
```

Expected: FAIL because bundle/workflow output does not yet expose compare-focus metadata.

**Step 3: Implement minimal bundle wiring**

Update the bundle builder to:

- build compare-focus metadata from existing compare summaries
- preserve one default focus per comparison
- avoid recomputing scalar or layer deltas

Only thread existing data forward.

**Step 4: Run test to verify it passes**

Run:

```powershell
python -m pytest tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/pipeline/test_visualization_packaging_workflow.py -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add src/llm_sched/analysis/visualization_bundle_builder.py src/llm_sched/contracts/visualization_catalog.py tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/pipeline/test_visualization_packaging_workflow.py
git commit -m "feat: thread compare focus modes into visualization bundle"
```

### Task 3: Add catalog compare-focus controls and workspace drilldown

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\src\llm_sched\visualization\catalog_builder.py`
- Test: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\visualization\test_catalog_builder.py`
- Test: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\pipeline\test_visualization_catalog_workflow.py`

**Step 1: Write the failing catalog tests**

Add tests proving generated catalog assets expose:

- a compare-focus selector
- focus-aware workspace summaries
- focus-aware deep links/export metadata

Cover both scalar-focused and layer-focused modes.

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py -q
```

Expected: FAIL because catalog assets only track panel, scope, and layer-delta focus today.

**Step 3: Implement minimal catalog support**

Extend the static JS builder so catalog workspace:

- stores the selected compare focus in URL state
- renders mode-appropriate summaries without changing underlying compare math
- preserves the selected focus in workspace JSON/SVG export metadata and workbench links

Prefer new helpers over inlining more branching inside large row-rendering functions.

**Step 4: Run test to verify it passes**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add src/llm_sched/visualization/catalog_builder.py tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py
git commit -m "feat: add compare focus modes to catalog workspace"
```

### Task 4: Add workbench sweep compare-focus support

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\src\llm_sched\visualization\workbench_builder.py`
- Test: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\visualization\test_workbench_builder.py`
- Test: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\pipeline\test_visualization_workbench_workflow.py`

**Step 1: Write the failing workbench tests**

Add tests proving generated workbench assets expose:

- compare-focus state in sweep-panel UI and URL hydration
- focus-aware summary rendering
- focus-aware JSON/SVG snapshot metadata

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q
```

Expected: FAIL because workbench sweep state currently tracks candidate and layer focus but not compare focus.

**Step 3: Implement minimal workbench wiring**

Update the workbench builder to:

- expose the same compare-focus options as catalog
- hydrate/persist compare focus in URL state
- render focus-aware sweep summaries and snapshot metadata

Reuse the same naming and fallback behavior as catalog workspace.

**Step 4: Run test to verify it passes**

Run:

```powershell
python -m pytest tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add src/llm_sched/visualization/workbench_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_workbench_workflow.py
git commit -m "feat: add compare focus modes to sweep workbench"
```

### Task 5: Run focused end-to-end verification

**Files:**
- Read: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\README.md`
- Read: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\docs/development/evaluation-compiler-roadmap.md`
- Read/Modify if needed: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\docs/plans/2026-03-20-spec-16-compare-focus-modes.md`

**Step 1: Run the focused verification ladder**

Run:

```powershell
python -m pytest tests/unit/contracts/test_visualization_bundle.py tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py -q
python -m pytest tests/unit/pipeline/test_visualization_packaging_workflow.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q
python -m pytest tests/smoke/test_cli_run_visualization_packaging.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q
```

Expected: PASS.

**Step 2: Record the slice outcome**

If implementation reality changes the chosen focus taxonomy or payload shape, update:

- `docs/development/evaluation-compiler-roadmap.md`
- this plan doc's completion notes

Keep the roadmap as the only status source.

**Step 3: Commit**

```bash
git add docs/development/evaluation-compiler-roadmap.md docs/plans/2026-03-20-spec-16-compare-focus-modes.md
git commit -m "docs: record spec16 compare focus mode closure"
```

## Completion Notes

- Completed on 2026-03-20 in `D:\workspace\llmSched\.worktrees\spec16-compare-modes`.
- Final compare focus taxonomy stayed aligned with the planned five-mode set:
  - `summary`
  - `memory-pressure`
  - `schedule-shape`
  - `estimated-layer`
  - `fitted-layer`
- Implementation outcome:
  - shared compare focus metadata now ships in visualization bundle compare summaries
  - visualization packaging synthesizes the same focus surface for standalone compare reports and raw sweep comparisons
  - catalog preserves compare focus in workspace URL state, workbench deep links, and export metadata
  - workbench preserves compare focus in URL hydration, sweep snapshot metadata, and JSON export payloads
- Verification evidence:
  - `python -m pytest tests/unit/contracts/test_visualization_bundle.py tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py -q` -> `18 passed`
  - `python -m pytest tests/unit/pipeline/test_visualization_packaging_workflow.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q` -> `13 passed`
  - `python -m pytest tests/smoke/test_cli_run_visualization_packaging.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q` -> `10 passed`
- Follow-on recommendation:
  - keep `SPEC-16` as the mainline blocker and extend the compare-focus payload with richer layer-level diff semantics or broader compare grouping before reopening `SPEC-19`-only polish work
