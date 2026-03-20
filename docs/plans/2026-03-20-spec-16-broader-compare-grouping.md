# SPEC-16 Broader Compare Grouping Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expand compare focus beyond the current summary-plus-pressure-plus-layer surface by promoting stable grouped scalar sections into first-class compare focus modes and making catalog/workbench render them accordingly.

**Architecture:** Keep Phase D compare math unchanged. Extend the shared compare-focus taxonomy to include grouped scalar sections that already exist in compare summaries, thread that richer focus set through bundle/catalog payloads, and make catalog/workbench render helpers emphasize the grouped section that matches the selected focus.

**Tech Stack:** Python, Pydantic contracts, static visualization builders, generated JavaScript, pytest

---

### Task 1: Extend shared compare-focus taxonomy for grouped scalar sections

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\src\llm_sched\compare_grouping.py`
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\src\llm_sched\contracts\visualization_bundle.py`
- Test: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\contracts\test_visualization_bundle.py`

**Step 1: Write the failing contract test**

Add a test proving visualization compare summaries accept the broader focus set:

- `summary`
- `throughput-latency`
- `phase-shape`
- `memory-pressure`
- `schedule-shape`
- `estimated-layer`
- `fitted-layer`

Assert that grouped scalar focuses carry compact summary labels tied to the corresponding grouped section.

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/contracts/test_visualization_bundle.py -q
```

Expected: FAIL because the broader compare focus ids do not exist yet.

**Step 3: Implement the minimal shared surface**

Add:

- new grouped-section compare focus ids and titles
- shared helper mapping compare focus ids to grouped scalar sections where applicable
- additive bundle contract compatibility through the existing compare summary focus metadata

**Step 4: Run test to verify it passes**

Run:

```powershell
python -m pytest tests/unit/contracts/test_visualization_bundle.py -q
```

Expected: PASS.

### Task 2: Emit broader compare focus metadata from visualization packaging

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\src\llm_sched\analysis\visualization_bundle_builder.py`
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\src\llm_sched\contracts\visualization_catalog.py`
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\src\llm_sched\pipeline\visualization_catalog.py`
- Test: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\analysis\test_visualization_bundle_builder.py`
- Test: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\pipeline\test_visualization_packaging_workflow.py`
- Test: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\pipeline\test_visualization_catalog_workflow.py`

**Step 1: Write the failing builder/workflow tests**

Add assertions proving:

- bundle compare summaries now emit `throughput-latency` and `phase-shape` focus modes when those grouped sections exist
- raw sweep comparisons and standalone compare reports preserve the same broader focus set
- catalog artifacts carry the broader focus modes through to generated payloads

**Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/pipeline/test_visualization_packaging_workflow.py tests/unit/pipeline/test_visualization_catalog_workflow.py -q
```

Expected: FAIL because packaging currently emits only the narrower compare focus set.

**Step 3: Implement minimal packaging support**

Update bundle/catalog builders to:

- emit grouped-section focus modes from existing `scalar_delta_groups`
- preserve the current default focus behavior
- avoid recomputing compare math outside the existing grouped scalar data

**Step 4: Run tests to verify they pass**

Run:

```powershell
python -m pytest tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/pipeline/test_visualization_packaging_workflow.py tests/unit/pipeline/test_visualization_catalog_workflow.py -q
```

Expected: PASS.

### Task 3: Make catalog compare rendering focus-aware for broader grouped sections

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\src\llm_sched\visualization\catalog_builder.py`
- Test: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\visualization\test_catalog_builder.py`

**Step 1: Write the failing catalog test**

Add assertions proving generated catalog assets:

- expose the new grouped compare focus labels
- include focus-aware grouped compare rendering helpers
- preserve the selected grouped compare focus in workspace summaries/export metadata

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py -q
```

Expected: FAIL because catalog compare rendering does not yet distinguish grouped scalar focuses beyond the current narrow set.

**Step 3: Implement minimal catalog support**

Update catalog JS so compare rendering:

- maps active compare focus to the relevant grouped scalar sections
- narrows grouped compare summaries for `summary`, `throughput-latency`, and `phase-shape`
- keeps existing pressure and layer flows intact

**Step 4: Run test to verify it passes**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py -q
```

Expected: PASS.

### Task 4: Make workbench sweep compare rendering focus-aware for broader grouped sections

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\src\llm_sched\visualization\workbench_builder.py`
- Test: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\visualization\test_workbench_builder.py`
- Test: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\pipeline\test_visualization_workbench_workflow.py`

**Step 1: Write the failing workbench tests**

Add tests proving generated workbench assets:

- expose the broader grouped compare focus labels
- include focus-aware grouped compare rendering helpers for sweep summaries
- preserve grouped compare focus in sweep export/snapshot metadata

**Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q
```

Expected: FAIL because workbench grouped compare rendering still treats grouped scalar content as an all-sections block.

**Step 3: Implement minimal workbench support**

Update workbench JS to:

- select grouped scalar sections based on active compare focus
- keep pressure/layer-specific compare behavior untouched
- reuse the same focus naming and fallback behavior as catalog

**Step 4: Run tests to verify they pass**

Run:

```powershell
python -m pytest tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q
```

Expected: PASS.

### Task 5: Run focused verification and record closure

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\docs\plans\2026-03-20-spec-16-broader-compare-grouping.md`

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

- the broader grouped compare focus set
- catalog/workbench grouped compare rendering adoption
- the next remaining `SPEC-16` gap after this slice

**Step 3: Commit**

```bash
git add docs/development/evaluation-compiler-roadmap.md docs/plans/2026-03-20-spec-16-broader-compare-grouping.md
git commit -m "docs: record spec16 broader compare grouping closure"
```

## Completion Notes

- Completed on 2026-03-20 in `D:\workspace\llmSched\.worktrees\spec16-compare-modes`.
- Final broader grouped compare focus taxonomy:
  - `summary`
  - `throughput-latency`
  - `phase-shape`
  - `memory-pressure`
  - `schedule-shape`
  - `estimated-layer`
  - `fitted-layer`
- Implementation outcome:
  - shared compare focus metadata now promotes `throughput-latency` and `phase-shape` into first-class grouped compare focuses
  - visualization packaging and catalog artifacts emit the broader grouped focus set directly from `scalar_delta_groups`
  - catalog compare rendering now narrows grouped scalar sections by active compare focus
  - workbench sweep compare rendering now applies the same grouped-focus selection logic as catalog
- Verification evidence:
  - `python -m pytest tests/unit/contracts/test_visualization_bundle.py tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py -q` -> `18 passed`
  - `python -m pytest tests/unit/pipeline/test_visualization_packaging_workflow.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q` -> `13 passed`
  - `python -m pytest tests/smoke/test_cli_run_visualization_packaging.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q` -> `10 passed`
- Follow-on recommendation:
  - keep `SPEC-16` as the mainline blocker and move next to deeper compare/workspace drill-down on top of the now-stable grouped focus, pressure, and layer diff payload
