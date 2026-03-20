# SPEC-16 Workspace Analysis Flow Surface Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Turn the current `workspace_analysis_flow` layer into a more complete analyst-facing workflow surface across row links, focused drill-down, and export metadata.

**Architecture:** Keep compare payloads unchanged. Reuse the existing flow-to-preset mapping and thread it through row-level links, focused workspace summary rendering, and export metadata so all three surfaces speak the same flow language.

**Tech Stack:** Python, static visualization builders, generated JavaScript, pytest

---

### Task 1: Add failing catalog coverage for the broader analysis-flow surface

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\visualization\test_catalog_builder.py`

**Step 1: Write the failing test**

Add assertions proving generated catalog assets:

- expose a helper such as `buildWorkspaceRowAnalysisFlowLink`
- render `Analysis Flow Summary` in the focused workspace card path
- preserve a human-readable active-flow summary in export metadata

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py -q
```

Expected: FAIL because the broader analysis-flow surface does not exist yet.

### Task 2: Implement the bundled analysis-flow surface

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\src\llm_sched\visualization\catalog_builder.py`

**Step 1: Add shared row-level flow helper**

Implement one helper for row-level flow links and thread it through the most natural cells.

**Step 2: Add focused workspace flow summary**

Render a compact summary block describing:

- active analysis flow label
- resolved preset
- resolved primary and secondary compare sections

**Step 3: Strengthen export metadata**

Add one human-readable header row and one structured field for the resolved active flow summary.

**Step 4: Run the focused catalog test**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py -q
```

Expected: PASS.

### Task 3: Preserve the broader surface in workflow and smoke outputs

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\pipeline\test_visualization_catalog_workflow.py`
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\smoke\test_cli_run_visualization_catalog.py`

**Step 1: Write the failing assertions**

Add assertions proving generated outputs include:

- row-level analysis-flow links
- focused flow-summary strings
- export metadata strings for active-flow summary

**Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: FAIL because generated outputs do not yet include the broader analysis-flow surface.

**Step 3: Re-run after implementation**

Once builder changes land, rerun:

```powershell
python -m pytest tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: PASS.

### Task 4: Record the slice in roadmap and plan notes

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\docs\plans\2026-03-20-spec-16-workspace-analysis-flow-surface.md`

**Step 1: Update roadmap checkpoint**

Record:

- row-level analysis-flow shortcuts
- focused flow-summary surface
- stronger export continuity

**Step 2: Update plan completion notes**

Add:

- verification commands run
- test counts
- the next remaining `SPEC-16` gap after this slice

### Task 5: Run focused verification

**Files:**
- No file changes required

**Step 1: Run focused verification**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: PASS.

## Completion

- Status: completed on 2026-03-20
- Implemented:
  - row-level analysis-flow shortcuts in the workspace overview
  - a focused workspace `Analysis Flow Summary` block
  - stronger export continuity via structured and human-readable active-flow summary metadata
- Verification:
  - `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q` -> `17 passed`
- Next:
  - richer compare interaction above the current analysis-flow-backed workspace surface
