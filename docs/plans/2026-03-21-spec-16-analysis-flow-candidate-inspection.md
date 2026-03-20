# SPEC-16 Analysis Flow Candidate Inspection Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Let active analysis flows rank workspace candidates, explain why they matter, and preserve that recommendation context in focused drill-down and exports.

**Architecture:** Reuse existing workspace row state, add a flow-aware recommendation layer above current summary/pressure/layer data, and thread the resulting recommendation metadata through workspace rows, focused drill-down, and export payloads without changing compare contracts.

**Tech Stack:** Python, static visualization builders, generated JavaScript, pytest

---

### Task 1: Add failing catalog tests for recommendation-aware candidate inspection

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\visualization\test_catalog_builder.py`

**Step 1: Write failing assertions**

Add assertions proving generated catalog assets:

- expose a helper such as `resolveWorkspaceAnalysisFlowRecommendation`
- render analyst-facing recommendation strings such as `Recommended For Current Flow`
- preserve structured recommendation metadata in workspace export payloads

**Step 2: Run the focused catalog test to verify RED**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py -q
```

Expected: FAIL because recommendation-aware candidate inspection does not exist yet.

### Task 2: Implement recommendation-aware workspace row and focused-card surfaces

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\src\llm_sched\visualization\catalog_builder.py`

**Step 1: Add flow-aware recommendation helpers**

Compute one recommendation object from the existing row state and active analysis flow.

**Step 2: Thread recommendation metadata into row state**

Expose recommendation score, tier, and reason alongside current row summary fields.

**Step 3: Render recommendation surfaces**

Add:

- a row-level recommendation tag/reason
- a focused-card recommendation summary block for the focused candidate

**Step 4: Re-run the focused catalog test**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py -q
```

Expected: PASS.

## Completion

- Status: completed on 2026-03-21
- Implemented:
  - flow-aware recommendation scoring and reason strings for catalog workspace candidates
  - focused workspace `Analysis Flow Candidate Recommendation` summary
  - structured recommendation continuity in workspace export metadata
- Verification:
  - `python -m pytest tests/unit/visualization/test_catalog_builder.py -q` -> `4 passed`
  - `python -m pytest tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q` -> `13 passed`
- Next:
  - richer compare interaction above the current analysis-flow-ranked candidate inspection surface

### Task 3: Preserve recommendation context in workspace export payloads

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\src\llm_sched\visualization\catalog_builder.py`
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\pipeline\test_visualization_catalog_workflow.py`
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\smoke\test_cli_run_visualization_catalog.py`

**Step 1: Extend export data**

Preserve:

- focused recommendation summary
- per-row recommendation metadata

**Step 2: Add workflow/smoke assertions**

Assert generated assets include recommendation helpers, labels, and export fields.

**Step 3: Run the focused workflow/smoke set**

Run:

```powershell
python -m pytest tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: PASS.

### Task 4: Record the slice and run focused verification

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\docs\plans\2026-03-21-spec-16-analysis-flow-candidate-inspection.md`

**Step 1: Update roadmap checkpoint**

Record:

- flow-ranked candidate recommendations
- focused recommendation summary
- export continuity for recommendation metadata

**Step 2: Update plan completion notes**

Add:

- verification commands run
- test counts
- next remaining `SPEC-16` gap after this slice

**Step 3: Run focused verification**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: PASS.
